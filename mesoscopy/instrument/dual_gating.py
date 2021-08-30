""" virtual instrument to sweep simultaneously two channels of the
Keithley 2600
"""

from typing import Union, Tuple, Optional
from scipy.constants import e, epsilon_0
import numpy as np
from warning import warn

from qcodes.instruments.parameters import _BaseParameter, \
    ParameterWithSetpoints
from qcodes.utils.helpers import abstractmethod


class DoubleGate:
    def __init__(self,
                 n: Union[np.array, float],
                 D: Union[np.array, float],
                 Ctg: float,
                 Cbg: float
                 ):
        if len(n) != len(D):
            warn('n and D should have the same dimensions')
        self.n = n
        self.D = D
        self.ctg = Ctg
        self.cbg = Cbg

    def top_gate_voltage(self):
        return (e*self.n + 2*epsilon_0*self.D)/2/self.ctg

    def back_gate_voltage(self):
        return (e*self.n - 2*epsilon_0*self.D)/2/self.cbg

    def coef(self):
        # TODO: change this so that it doesn't only accept constant n
        return self.ctg/self.cbg

    def intercept(self):
        # TODO: same
        return self.back_gate()[0] - self.top_gate()[0] * self.coef

    def print_equation(self):
        print(f'V_b = {round(self.coef,3)} * V_t + {round(self.intercept,3)}')


class DensityParameter(ParameterWithSetpoints):
    """ create a density parameter for maps at constant displacement"""
    def __init__(self, name: str,
                 gates: Tuple[_BaseParameter, _BaseParameter],
                 capacitances: Tuple[float, float],
                 *args, **kwargs) -> None:
        super().__init__(name=name,
                         setpoints=list[gates],
                         *args, **kwargs)
        self._vtg = gates[0]
        self._vbg = gates[1]
        self._ctg = capacitances[0]
        self._cbg = capacitances[1]

    @property
    def vtg(self):
        for param in self._vtg:
            return param.get()

    @vtg.setter
    def vtg(self, value):
        for param in self._vtg:
            param.set(value)

    @property
    def vbg(self):
        for param in self._vbg:
            return param.get()

    @vbg.setter
    def vbg(self, value):
        for param in self._vbg:
            param.set(value)

    def D(self):
        return (self._ctg*self.vtg() - self._cbg*self.vbg())/2/epsilon_0

    @abstractmethod
    def get_raw(self):
        return (self._ctg*self.vtg() + self._cbg*self.vbg())/e

    @abstractmethod
    def set_raw(self, value):
        self.vtg((e*value + 2*epsilon_0*self.D)/2/self._ctg)
        self.vbg((e*value - 2*epsilon_0*self.D)/2/self._cbg)


class DisplacementParameter(ParameterWithSetpoints):
    """ create displacement parameter"""
    def __init__(self, name: str,
                 gates: Tuple[_BaseParameter, _BaseParameter],
                 capacitances: Tuple[float, float],
                 n: Optional[float],
                 *args, **kwargs) -> None:
        super().__init__(name=name,
                         setpoints=list[gates],
                         *args, **kwargs)
