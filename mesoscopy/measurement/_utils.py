"""
Some utils used in sweeps
"""

import time
import numpy as np
from qcodes.instrument.parameter import _BaseParameter
from qcodes import validators

def _is_monotonic(array):
    """
    check if array is monotonic
    """
    return np.all(np.diff(array) > 0) or np.all(np.diff(array) < 0)


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
        self._conut = 0

    def get_raw(self):
        out = self.outer_count
        self._count += 1
        return out

    def reset_count(self) -> None:
        self._count = 0
