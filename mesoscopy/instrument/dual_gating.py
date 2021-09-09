""" virtual instrument to sweep simultaneously two channels of the
Keithley 2600
"""

from typing import Tuple, Optional
from scipy.constants import e, epsilon_0

from qcodes.instrument.parameter import _BaseParameter, Parameter


class DensityParameter(Parameter):
    """ density parameter for maps at constant density

    Args:
        ``gates``: tuple[Parameter, Parameter]. the parameter to sweep for top
            gate and back gate, respectively.
        ``capacitances``: tuple[float, float]. capacitance for top gate and
            back gate, respectively, in F/m
        ``lock_D``: bool. If true, when we sweep the parameter, it will be done
            at the displacement when parameter is initialised. If false, it
            will follow the density of previous measurement, with possible
            drifts.
    """
    def __init__(self, name: str,
                 gates: Tuple[_BaseParameter, _BaseParameter],
                 capacitances: Tuple[float, float],
                 lock_D: Optional[bool] = False,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._vtg = gates[0]
        self._vbg = gates[1]
        self._ctg = capacitances[0]
        self._cbg = capacitances[1]
        self._D = (self._ctg/self._vtg() - self._cbg/self._vbg())/2/epsilon_0
        self._lockD = lock_D
        self._instrument = gates[0].root_instrument

    @property
    def D(self):
        return(self._ctg*self._vtg() - self._cbg*self._vbg())/2/epsilon_0

    @property
    def max_rate(self):
        if self._vtg.max_rate():
            vtg_maxrate = self._vtg.max_rate()*self._ctg
        elif self._vtg._instrument.max_rate():
            vtg_maxrate = self._vtg._instrument.max_rate()*self._ctg
        else:
            vtg_maxrate = 0

        if self._vbg.max_rate():
            vbg_maxrate = self._vbg.max_rate()*self._cbg
        elif self._vbg._instrument.max_rate():
            vbg_maxrate = self._vbg._instrument.max_rate()*self._cbg
        else:
            vbg_maxrate = 0

        if not vtg_maxrate:
            return vbg_maxrate/e
        elif not vbg_maxrate:
            return vtg_maxrate/e
        else:
            return min(vtg_maxrate, vbg_maxrate)/e

    def get_raw(self):
        return (self._ctg*self._vtg() + self._cbg*self._vbg())/e

    def set_raw(self, value):
        if self._lockD:
            displacement = self._D
        else:
            displacement = self.D
        self._vtg((e*value + 2*epsilon_0*displacement)/2/self._ctg)
        self._vbg((e*value - 2*epsilon_0*displacement)/2/self._cbg)


class DisplacementParameter(Parameter):
    """ displacement parameter for maps at constant density

    Args:
        ``gates``: tuple[Parameter, Parameter]. the parameter to sweep for top
            gate and back gate, respectively.
        ``capacitances``: tuple[float, float]. capacitance for top gate and
            back gate, respectively, in F/m
        ``lock_n``: bool. If true, when we sweep the parameter, it will be done
            at the density when parameter is initialised. If false, it will
            follow the density of previous measurement, with possible drifts
    """
    def __init__(self, name: str,
                 gates: Tuple[_BaseParameter, _BaseParameter],
                 capacitances: Tuple[float, float],
                 lock_n: Optional[bool] = False,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._vtg = gates[0]
        self._vbg = gates[1]
        self._ctg = capacitances[0]
        self._cbg = capacitances[1]
        self._n = (self._ctg/self._vtg() + self._cbg/self._vbg())/e
        self._lockn = lock_n
        self._instrument = gates[0].root_instrument

    @property
    def n(self):
        return(self._ctg*self._vtg() + self._cbg*self._vbg())/e

    @property
    def max_rate(self):
        if self._vtg.max_rate():
            vtg_maxrate = self._vtg.max_rate()*self._ctg
        elif self._vtg._instrument.max_rate():
            vtg_maxrate = self._vtg._instrument.max_rate()*self._ctg
        else:
            vtg_maxrate = 0

        if self._vbg.max_rate():
            vbg_maxrate = self._vbg.max_rate()*self._cbg
        elif self._vbg._instrument.max_rate():
            vbg_maxrate = self._vbg._instrument.max_rate()*self._cbg
        else:
            vbg_maxrate = 0

        if not vtg_maxrate:
            return vbg_maxrate/2/epsilon_0
        elif not vbg_maxrate:
            return vtg_maxrate/2/epsilon_0
        else:
            return min(vtg_maxrate, vbg_maxrate)/2/epsilon_0

    def get_raw(self):
        return (self._ctg*self._vtg() - self._cbg*self._vbg())/2/epsilon_0

    def set_raw(self, value):
        if self._lockn:
            density = self._n
        else:
            density = self.n
        self._vtg((e*density + 2*epsilon_0*value)/2/self._ctg)
        self._vbg((e*density - 2*epsilon_0*value)/2/self._cbg)


class LinearParameter(Parameter):
    """a parameter two fix a linear relation between two parameters as:
        ``dependent_param = m * primary_param + p``


    Args:
        ``primary_param``: Parameter to sweep
        ``dependent_param``: Parameter that will be swept as a function of
            ``primary_param``
        ``m``: float, coefficient for the linear relation
        ``p``: float, intercept in the linear relation
    """
    def __init__(self, name: str,
                 primary_param: _BaseParameter,
                 dependent_param: _BaseParameter,
                 m: float,
                 p: float,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._x = primary_param
        self._y = dependent_param
        self._m = m
        self._p = p

        @property
        def max_rate(self):
            if self._x.max_rate():
                return self._x.max_rate()
            elif self._x._instrument.max_rate():
                return self._x._instrument.max_rate()
            else:
                return None

        def get_raw(self):
            return self._x

        def set_raw(self, value):
            self._y(self._m * self._x + self._p)
