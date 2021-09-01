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

        # .1V/sec means .1V/1000ms.
        # so each 10ms we sweep 10/1000 *speed


def _safesweep_to(target, param: _BaseParameter):
    init = param.get()
    array = generate_1D_sweep_array(init, target, step=.02)
    time.sleep(.05)
    for v in array:
        param.set(v)
        time.sleep(0.01)
    time.sleep(.05)

