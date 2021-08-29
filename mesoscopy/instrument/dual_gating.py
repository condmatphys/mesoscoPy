""" virtual instrument to sweep simultaneously two channels of the
Keithley 2600
"""

from typing import Union
from scipy.constants import e, epsilon_0
import numpy as np
from warning import warn

from qcodes.instruments.parameters import ParameterWithSetpoints


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
    def get_raw(self):
        # measure vtg, vbg. with knowledge of ctg, cbg,
        # return n

    def set_raw(self):
        # needs knowledge of ctg, cbg, D
        # sets vtg, vbg




