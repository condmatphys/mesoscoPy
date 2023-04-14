"""
Some utils used in sweeps
"""

import time
from numpy import all, diff
from qcodes import Parameter
from qcodes import validators
from qcodes.instrument.parameter import _BaseParameter

from .array import generate_lin_array


def _is_monotonic(array):
    """
    check if array is monotonic
    """
    return all(diff(array) > 0) or all(diff(array) < 0)


def _safesweep_to(target, param: _BaseParameter):
    """
    function to sweep slowly to the next value in an array (target)
    """
    if hasattr(param, 'max_rate') and param.max_rate() > 0:
        step = param.max_rate()/100
        init = param.get()
        array = generate_lin_array(init, target, step=step)
    elif hasattr(param._instrument, 'max_rate') and \
            param._instrument.max_rate() > 0:
        step = param._instrument.max_rate()/100
        init = param.get()
        array = generate_lin_array(init, target, step=step)
    else:
        array = [target]
    for v in array:
        param.set(v)
        time.sleep(0.01)
    time.sleep(.0001)


def _threshold(param: _BaseParameter, threshold=1e-9):
    if param.get() > threshold:
        return True
    else:
        return False
