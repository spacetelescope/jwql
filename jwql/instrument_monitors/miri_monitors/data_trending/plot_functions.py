import numpy as np

def split_data(value):
    x = []
    y = []
    for item in value:
        x.append(item[0])
        y.append(item[1])
    X = np.array(x)
    Y = np.array(y)
    return X,Y


def pol_regression(x, y, rank):
    z = np.polyfit(x, y, rank)
    f = np.poly1d(z)
    y_poly = f(x)
    return y_poly
