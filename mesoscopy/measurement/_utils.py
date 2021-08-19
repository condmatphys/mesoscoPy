"""
Some utils used in sweeps
"""

import numpy as np

def _is_monotonic(array):
    """
    check if array is monotonic
    """
    return np.all(np.diff(array) > 0) or np.all(np.diff(array) < 0)
