"""
Some utils used in sweeps
"""

import time
from numpy import all, diff
from qcodes import Parameter
from qcodes import validators
from qcodes.instrument.parameter import _BaseParameter

from.array import generate_1D_sweep_array


def _is_monotonic(array):
    """
    check if array is monotonic
    """
    return all(diff(array) > 0) or all(diff(array) < 0)


class CountParameter(Parameter):
    """ parameter to keep track of how many sweep we make """

    def __init__(self,
                 name: str,
                 label: str = 'counter',
                 **kwargs
                 ):
        kwarg = ['unit', 'get_cmd', 'set_cmd']

        for kw in kwarg:
            if kw in kwarg:
                raise ValueError(f'cannot set `{kw}` for a `CountParameter`')

        super().__init__(name,
                         label=label,
                         unit='#',
                         validators=validators.Ints(min_value=0),
                         set_cmd=False, **kwargs)
        self._count = 0

    def get_raw(self):
        out = self.outer_count
        self._count += 1
        return out

    def reset_count(self) -> None:
        self._count = 0


def _safesweep_to(target, param: _BaseParameter):
    """
    function to sweep slowly to the next value in an array (target)
    """
    if hasattr(param, 'max_rate') and param.max_rate() > 0:
        step = param.max_rate()/100
        init = param.get()
        array = generate_1D_sweep_array(init, target, step=step)
    elif hasattr(param._instrument, 'max_rate') and \
            param._instrument.max_rate() > 0.:
        step = param._instrument.max_rate()/100
        init = param.get()
        array = generate_1D_sweep_array(init, target, step=step)
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
