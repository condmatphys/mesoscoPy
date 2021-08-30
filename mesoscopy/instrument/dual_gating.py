""" virtual instrument to sweep simultaneously two channels of the
Keithley 2600
"""

from typing import Tuple
from scipy.constants import e, epsilon_0

from qcodes.instruments.parameters import _BaseParameter, \
    ParameterWithSetpoints
from qcodes.utils.helpers import abstractmethod


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
    """ create a displacement parameter for maps at constant density"""
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

    def n(self):
        return (self._ctg*self.vtg() + self._cbg*self.vbg())/e

    @abstractmethod
    def get_raw(self):
        return (self._ctg*self.vtg() - self._cbg*self.vbg())/2/epsilon_0

    @abstractmethod
    def set_raw(self, value):
        self.vtg((e*self.n + 2*epsilon_0*value)/2/self._ctg)
        self.vbg((e*self.n - 2*epsilon_0*value)/2/self._cbg)
