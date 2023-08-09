from time import time
from qcodes import Parameter
from typing import Tuple
from qcodes import Instrument
from qcodes.utils.validators import Ints, Numbers
from qcodes.instrument.parameter import _BaseParameter
from qcodes.instrument.specialized_parameters import ElapsedTimeParameter as \
    TimeParameter
from scipy.constants import e, epsilon_0


class CountParameter(Parameter):
    """ parameter to keep track of how many sweep we make """

    def __init__(self,
                 name: str,
                 label: str = 'counter',
                 **kwargs
                 ):
        hardcoded_kwargs = ['unit', 'get_cmd', 'set_cmd']

        for hck in hardcoded_kwargs:
            if hck in kwargs:
                raise ValueError(f'cannot set `{hck}` for a `CountParameter`')

        super().__init__(name,
                         label=label,
                         unit='#',
                         vals=Ints(min_value=0),
                         set_cmd=False, **kwargs)
        self._count = 0

    def get_raw(self):
        out = self.outer_count
        self._count += 1
        return out

    def reset_count(self) -> None:
        self._count = 0


class Counter(Instrument):
    '''an instrument to use as counter'''
    def __init__(self, name: str = 'counter',
                **kwargs):
        super().__init__(name, **kwargs)

        self.add_parameter(
            'counter',
            parameter_class=Parameter,
            initial_value=0,
            label=f"counter",
            unit="#",
            vals=Numbers(min_value=0),
            get_cmd=None,
            set_cmd=None,
            )


class TimestampParameter(Parameter):
    '''parameter to keep track of time, gives a timestamp'''

    def __init__(self,
                 name: str,
                 label: str = 'timestamp',
                 **kwargs):
        hardcoded_kwargs = ['unit', 'get_cmd', 'set_cmd']
        for hck in hardcoded_kwargs:
            if hck in kwargs:
                raise ValueError(f'cannot set `{hck}` for a `TimestampParameter`')

        super().__init__(name=name,
                         label=label,
                         unit='s',
                         set_cmd=False,
                         **kwargs)


    def get_raw(self) -> float:
        return time()

# ----------------------
# Dual gating parameters
# ----------------------


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
                 lockD: bool = False,
                 displacement: float = 0,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._vtg = gates[0]
        self._vbg = gates[1]
        self._ctg = capacitances[0]
        self._cbg = capacitances[1]
        self._D = displacement
        self._lockD = lockD
        self._instrument = gates[0].root_instrument

        if hasattr(self._vtg, 'max_rate'):
            vtg_maxrate = self._vtg.max_rate() * self._ctg
        elif hasattr(self._vtg._instrument, 'max_rate'):
            vtg_maxrate = self._vtg._instrument.max_rate() * self._ctg
        else:
            vtg_maxrate = 0

        if hasattr(self._vbg, 'max_rate'):
            vbg_maxrate = self._vbg.max_rate() * self._cbg
        elif hasattr(self._vbg._instrument, 'max_rate'):
            vbg_maxrate = self._vbg._instrument.max_rate() * self._cbg
        else:
            vbg_maxrate = 0

        if not vtg_maxrate:
            max_r = vbg_maxrate/e
        elif not vbg_maxrate:
            max_r = vtg_maxrate/e
        else:
            max_r = min(vtg_maxrate, vbg_maxrate)/e
        
        if hasattr(self._instrument, 'max_rate'):
            self._instrument.max_rate.set(max_r)
        else:
            self.max_rate = Parameter(
                'max_rate',
                unit='V/s',
                get_cmd=None,
                set_cmd=None,
                label='maximum sweeping rate',
                instrument=self._instrument,
                initial_value=max_r)

    @property
    def D(self):
        return(self._ctg*self._vtg() - self._cbg*self._vbg())/2/epsilon_0

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
                 lockn: bool = False,
                 density: float = 0,
                 *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._vtg = gates[0]
        self._vbg = gates[1]
        self._ctg = capacitances[0]
        self._cbg = capacitances[1]
        self._n = density
        self._lockn = lockn
        self._instrument = gates[0].root_instrument

        if hasattr(self._vtg, 'max_rate'):
            vtg_maxrate = self._vtg.max_rate() * self._ctg
        elif hasattr(self._vtg._instrument, 'max_rate'):
            vtg_maxrate = self._vtg._instrument.max_rate() * self._ctg
        else:
            vtg_maxrate = 0

        if hasattr(self._vbg, 'max_rate'):
            vbg_maxrate = self._vbg.max_rate() * self._cbg
        elif hasattr(self._vbg._instrument, 'max_rate'):
            vbg_maxrate = self._vbg._instrument.max_rate() * self._cbg
        else:
            vbg_maxrate = 0

        if not vtg_maxrate:
            max_r = vbg_maxrate/2/epsilon_0
        elif not vbg_maxrate:
            max_r = vtg_maxrate/2/epsilon_0
        else:
            max_r = min(vtg_maxrate, vbg_maxrate)/2/epsilon_0

        if hasattr(self._instrument, 'max_rate'):
            self._instrument.max_rate.set(max_r)
        else:
            self.max_rate = Parameter(
                'max_rate',
                unit='V/s',
                get_cmd=None,
                set_cmd=None,
                label='maximum sweeping rate',
                instrument=self._instrument,
                initial_value=max_r)

    @property
    def n(self):
        return(self._ctg*self._vtg() + self._cbg*self._vbg())/e

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
        self._instrument = primary_param.root_instrument

        if hasattr(self._x, 'max_rate'):
            vx_maxrate = self._x.max_rate()
        elif hasattr(self._x._instrument, 'max_rate'):
            vx_maxrate = self._x._instrument.max_rate()
        else:
            vx_maxrate = 0

        if hasattr(self._y, 'max_rate'):
            vy_maxrate = self._y.max_rate()/abs(self._m)
        elif hasattr(self._y._instrument, 'max_rate'):
            vy_maxrate = self._y._instrument.max_rate()/abs(self._m)
        else:
            vy_maxrate = 0

        if not vx_maxrate:
            max_r = vy_maxrate
        elif not vy_maxrate:
            max_r = vx_maxrate
        else:
            max_r = min(vx_maxrate, vy_maxrate)

        self.max_rate = Parameter(
            'max_rate',
            unit='V/s',
            get_cmd=None,
            set_cmd=None,
            label='maximum sweeping rate',
            instrument=self._instrument,
            initial_value=max_r
        )

    def get_raw(self):
        return self._x()

    def set_raw(self, value):
        self._x(value)
        self._y(self._m * value + self._p)
