import math
import numpy as np


def apply_hoeffding(n, t):
    bound = math.exp((-2 * n * (t ** 2)) / ((.005 + .005) ** 2))
    return bound
