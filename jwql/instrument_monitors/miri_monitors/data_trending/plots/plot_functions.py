import numpy as np

def split_data(value):
    x = []
    y1 = []
    y2 = []
    for item in value:
        x.append(item[0])
        y1.append(item[1])
        y2.append(item[2])
    X = np.array(x)
    Y1 = np.array(y1)
    Y2 = np.array(y2)
    return X,Y1,Y2


def pol_regression(x, y, rank):
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly
