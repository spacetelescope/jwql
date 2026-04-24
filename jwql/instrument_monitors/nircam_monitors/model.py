import os
import glob
import random
import numpy as np
from astropy.io import fits
from astropy.visualization import AsinhStretch
from PIL import Image
import django
from django import setup

try:
    from tqdm import tqdm
    from sklearn.metrics import roc_auc_score
except ImportError:
    raise ImportError("Anomaly detection requires `tqdm` and `sklearn` dependencies")

try:
    import torch
    import torch.nn as nn
    from torchvision import transforms
    import torchvision.models as models
    from torch.utils.data import Dataset, DataLoader
except ImportError:
    raise ImportError("dragon's breath prediction requires torch and torchvision dependencies")

from jwql.utils import monitor_utils
from jwql.utils.constants import ON_GITHUB_ACTIONS, ON_READTHEDOCS
from jwql.utils.logging_functions import log_info, log_fail
from jwql.utils.utils import get_config, filesystem_path

# django setup to access database models
if not ON_GITHUB_ACTIONS and not ON_READTHEDOCS:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jwql.website.jwql_proj.settings")
    setup()
    from jwql.website.apps.jwql.models import Anomalies, RootFileInfo

# ── Constants 
PATCH_SIZE  = 256
STRIDE      = 256
DETECTOR_H  = 2048
DETECTOR_W  = 2048


# load fits files
def load_rate_fits(path: str):
    """Load HDU[1] science array from rate FITS file."""
    with fits.open(path, memmap=False) as hdul:
        # science image in HDU 1
        img = hdul[1].data.astype(np.float32)
    img = np.nan_to_num(img, nan=0.0, posinf=0.0, neginf=0.0)
    return img


def asinh_normalize(img, a=0.1, eps=1e-6):
    """Normalize image with AsinhStretch.

    Steps:
        1. Linear normalize to [0, 1]  →  y = (x - min) / (max - min)
        2. Apply AsinhStretch          →  y = asinh(x/a) / asinh(1/a)

    Parameters
    ----------
    img : np.ndarray
        Raw float32 science image.
    a : float
        AsinhStretch parameter. Smaller = more aggressive boost of faint
        values. Default 0.1 matches astropy default.
    eps : float
        Small value to avoid division by zero.

    Returns
    -------
    stretched : np.ndarray
        Float32 image in [0, 1].
    """

    # linear normalize to [0, 1]
    low = float(np.min(img))
    high = float(np.max(img))
    normalized = (img - low) / (high - low + eps)

    # asinh stretch
    stretch   = AsinhStretch(a=a)
    stretched = stretch(normalized).astype(np.float32)
    return stretched

def save_normalized_png(img: np.ndarray, out_path: str):
    """Save a float32 [0,1] normalized image as an 8-bit PNG."""
    uint8 = (img * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(uint8, mode="L").save(out_path)

def convert_fits_to_pngs(fits_paths: list, out_dir: str, a=0.1) -> list:
    """Normalize and save each FITS file as a PNG. Returns list of PNG paths."""
    os.makedirs(out_dir, exist_ok=True)
    png_paths = []
    for path in tqdm(fits_paths, desc="Converting FITS into PNG"):
        try:
            img = asinh_normalize(load_rate_fits(path), a=a)
            stem = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(out_dir, stem + ".png")
            save_normalized_png(img, out_path)
            png_paths.append(out_path)
        except Exception as e:
            print(f"  Skipping {path}: {e}")
    return png_paths


# 2) Fixed patch extraction  (8 × 8 = 64 patches per exposure)

def extract_patches(img, patch_size=PATCH_SIZE, stride=STRIDE):
    """Tile a 2D image into non-overlapping patches.

    For a 2048×2048 image with patch_size=256 and stride=256:
        positions per axis = floor((2048 - 256) / 256) + 1 = 8
        total patches      = 8 × 8 = 64

    Parameters
    ----------
    img : np.ndarray
        2D float32 normalized image.
    patch_size : int
        Height and width of each square patch.
    stride : int
        Step between patch origins (256 = no overlap).

    Returns
    -------
    patches : list of np.ndarray
        List of (patch_size × patch_size) float32 arrays.
    coords : list of tuple
        (y, x) top-left pixel coordinate of each patch.
    """
    H, W    = img.shape
    patches = []
    coords  = []

    # calculate patch positions based on stride
    y_positions = range(0, H - patch_size + 1, stride)
    x_positions = range(0, W - patch_size + 1, stride)

    # loop over patch positions and extract patches
    for y in y_positions:
        for x in x_positions:
            # extract patch and store with its top-left coordinate
            patch = img[y:y + patch_size, x:x + patch_size]
            # append patch and coordinate to lists
            patches.append(patch)
            coords.append((y, x))

    return patches, coords


def extract_patches_from_file(path, patch_size=PATCH_SIZE,
                               stride=STRIDE, a=0.1):
    """Load a FITS file, normalize, and extract all fixed patches.

    Parameters
    ----------
    fits_path : str
        Path to the _rate.fits file.
    patch_size : int
        Patch size in pixels.
    stride : int
        Stride between patches.
    a : float
        AsinhStretch parameter.

    Returns
    -------
    patches : list of np.ndarray
    coords  : list of (y, x) tuples
    """
    # load and normalize
    if path.endswith(".png"):
        img = np.array(Image.open(path), dtype=np.float32) / 255.0
    else:
        img = asinh_normalize(load_rate_fits(path), a=a)
    return extract_patches(img, patch_size=patch_size, stride=stride)


# 3) Build fixed patch inventory from file lists

def build_patch_inventory(anomaly_files, normal_files, patch_size=PATCH_SIZE, stride=STRIDE, a=0.1):
    """Extract all patches from all files and return flat lists.

    Parameters
    ----------
    anomaly_files : list of str
        Paths to Dragon's Breath FITS files.
    normal_files : list of str
        Paths to normal FITS files.
    patch_size : int
        Patch size in pixels.
    stride : int
        Stride between patches.
    a : float
        AsinhStretch parameter.

    Returns
    -------
    all_patches : list of np.ndarray
    all_labels  : list of int   (1 = anomaly, 0 = normal)
    """

    all_patches = []
    all_labels  = []

    for label, file_list in [(1, anomaly_files), (0, normal_files)]:
        name = "anomaly" if label == 1 else "normal"
        # tqdm for progress bar
        for path in tqdm(file_list, desc=f"Extracting {name} patches"):
            try:
                # extract patches from this file and add to inventory
                patches, _ = extract_patches_from_file(path, patch_size=patch_size, stride=stride, a=a)
                all_patches.extend(patches)
                all_labels.extend([label] * len(patches))
            except Exception as e:
                print(f"  Skipping {path}: {e}")

    print(f"Total patches: {len(all_patches)}  "f"(anomaly={sum(all_labels)}, normal={len(all_labels)-sum(all_labels)})")
    return all_patches, all_labels



# 4) Fixed patch dataset

class FixedPatchDataset(Dataset):
    """Dataset from a pre built patch inventory (no random sampling).

    Parameters
    ----------
    patches : list of np.ndarray
    labels  : list of int
    """
    def __init__(self, patches, labels):
        self.patches = patches
        self.labels  = labels

    def __len__(self):
        return len(self.patches)

    # returns one patch and label at a time, no random sampling
    def __getitem__(self, idx):
        # convert patch to tensor and add channel dimension
        x = torch.from_numpy(self.patches[idx]).unsqueeze(0)  # [1, H, W]
        # convert label to tensor
        y = torch.tensor(self.labels[idx], dtype=torch.long)
        return x, y



# 5) Model

def define_model_architecture():
    """Define the basic architecture of the ML model. This will be the framework into which
    the model parameters will be loaded, in order to fully define the function.

    Returns
    -------
    model : torchvision.models.resnet.ResNet
        ResNet model to use for prediction
    """
    # Load pre-trained ResNet-18 model
    model = models.resnet18(weights='IMAGENET1K_V1')

    # Modify the final fully connected layer for binary classification
    model.fc = nn.Linear(model.fc.in_features, 1)

    # Add a sigmoid activation after the final layer
    model.add_module('sigmoid', nn.Sigmoid())
    return model


# Evaluation function for accuracy and AUC
@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    # collect probabilities and labels for AUC calculation
    probs = []
    # correct and total for accuracy
    y_all = []
    correct = total = 0
    for x, y in loader:
        x, y   = x.to(device), y.to(device)
        logits  = model(x)
        # take probability of class 1 (anomaly) for AUC, and argmax for accuracy
        probs   = torch.softmax(logits, dim=1)[:, 1]
        pred    = torch.argmax(logits, dim=1)
        correct += (pred == y).sum().item()
        total   += y.numel()
        probs.extend(probs.cpu().numpy().tolist())
        y_all.extend(y.cpu().numpy().tolist())
    acc = correct / max(total, 1)
    auc = roc_auc_score(y_all, probs) if len(set(y_all)) > 1 else float("nan")
    return acc, auc

def get_files_from_db():
    """Pull Anomaly's and normal file paths from the JWQL database."""
    """To see specific files used in training refer to ML Onboarding Notes"""

    # pull all files with Dragon's Breath anomaly
    results = (
        RootFileInfo.objects
        .filter(anomalies__dragons_breath=True) # change to anomaly used
        .distinct())

    anomaly_files = []
    for r in results:
        filename = r.root_name + "_rate.fits"
        try:
            path = filesystem_path(filename, check_existence=True)
            anomaly_files.append(path)
        except Exception as e:
            print(f"Could not find {filename}: {e}")

    return anomaly_files

 
# 6) Main training loop
def main():

    # normal files locally
    base = "Datasets"
    norm_train = sorted(glob.glob(os.path.join(base, "normal", "training",   "*.fits")))
    norm_val   = sorted(glob.glob(os.path.join(base, "normal", "validation", "*.fits")))
    norm_test  = sorted(glob.glob(os.path.join(base, "normal", "testing",    "*.fits")))

    # split anomaly files from database
    all_anomaly_files = get_files_from_db()
    random.shuffle(all_anomaly_files)
    n = len(all_anomaly_files)

    # 70% train, 15% val, 15% test split
    n_train = int(0.70 * n)
    n_val   = int(0.15 * n)
    anom_train = all_anomaly_files[:n_train]
    anom_val   = all_anomaly_files[n_train:n_train + n_val]
    anom_test  = all_anomaly_files[n_train + n_val:]

    print(f"Anomaly split — train:{len(anom_train)} val:{len(anom_val)} test:{len(anom_test)}")
    print(f"Normal  split — train:{len(norm_train)} val:{len(norm_val)} test:{len(norm_test)}")

    # Convert all FITS files to PNGs
    anom_train_png = convert_fits_to_pngs(anom_train, "Datasets/anomaly/training")
    anom_val_png   = convert_fits_to_pngs(anom_val,   "Datasets/anomaly/validation")
    anom_test_png  = convert_fits_to_pngs(anom_test,  "Datasets/anomaly/testing")

    norm_train_png = convert_fits_to_pngs(norm_train, "Datasets/normal/training")
    norm_val_png   = convert_fits_to_pngs(norm_val,   "Datasets/normal/validation")
    norm_test_png  = convert_fits_to_pngs(norm_test,  "Datasets/normal/testing")
    
    # Build fixed patch inventories
    train_patches, train_labels = build_patch_inventory(anom_train_png, norm_train_png)
    val_patches, val_labels = build_patch_inventory(anom_val_png, norm_val_png)
    test_patches, test_labels = build_patch_inventory(anom_test_png, norm_test_png)

    # Datasets + loaders
    train_ds = FixedPatchDataset(train_patches, train_labels)
    val_ds   = FixedPatchDataset(val_patches,   val_labels)
    test_ds  = FixedPatchDataset(test_patches,  test_labels)

    train_loader = DataLoader(train_ds, batch_size=32, shuffle=True,  num_workers=2)
    val_loader   = DataLoader(val_ds,   batch_size=32, shuffle=False, num_workers=2)
    test_loader  = DataLoader(test_ds,  batch_size=32, shuffle=False, num_workers=2)

    # Model + optimizer
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    model     = make_resnet18_binary(1).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    criterion = nn.CrossEntropyLoss()

    # Training loop
    best_val_auc = -1 # -1 is worst possible AUC, so any real model should beat this baseline. We will save the model with the highest validation AUC.
    
    # train for 10 epochs
    for epoch in range(1, 11):
        model.train()
        running_loss = 0.0

        # tqdm for progress bar
        for x, y in tqdm(train_loader, desc=f"Epoch {epoch}"):
            x, y = x.to(device), y.to(device)
            # zero gradients, forward pass, compute loss, backward pass, and update weights
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        # compute average training loss and validation metrics
        train_loss = running_loss / max(len(train_loader), 1)
        val_acc, val_auc  = evaluate(model, val_loader, device)

        print(f"Epoch {epoch:02d} | train_loss={train_loss:.4f} | "
              f"val_acc={val_acc:.3f} | val_auc={val_auc:.3f}")

        # Save model if validation AUC improves
        if val_auc > best_val_auc:
            best_val_auc = val_auc
            # save the best model weights to a file
            torch.save(model.state_dict(), "anomaly_finder_ML_model.pt")

    # Final test
    model.load_state_dict(torch.load("anomaly_finder_ML_model.pt", map_location=device))
    test_acc, test_auc = evaluate(model, test_loader, device)
    print(f"\nTEST | acc={test_acc:.3f} | auc={test_auc:.3f}")




if __name__ == "__main__":
    main()
