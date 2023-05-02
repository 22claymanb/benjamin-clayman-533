import math
import numpy as np


def apply_hoeffding(n, t):
    bound = math.exp((-2 * n * (t ** 2)) / ((.01 + .01) ** 2))
    return bound
