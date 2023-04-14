"""
functions related to current and voltage sources
currently integrate only SRS CS580
"""

import configparser
import re
from functools import partial
import pyvisa
import logging
from traceback import format_exc
from typing import Optional, Any, Union, List, Dict
from numpy import array

from qcodes import IPInstrument, VisaInstrument, Parameter
from qcodes.instrument.parameter import _BaseParameter
from qcodes.utils.validators import Enum, Ints, Numbers
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes_contrib_drivers.drivers.Oxford.IPS120 import OxfordInstruments_IPS120

from time import sleep

class CS580(VisaInstrument):
    """
    Stanford CS580 Current source driver
    """

    _gains = {
        1e-9: 0, 10e-9: 1, 100e-9: 2,
        1e-6: 3, 10e-6: 4, 100e-6: 5,
        1e-3: 6, 10e-3: 7, 50e-3: 8}
    _n_to_gains = {g: k for k, g in _gains.items()}

    def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            terminator: str = '\r\n',
            **kwargs: Any):
        super().__init__(name, address=address, terminator=terminator, **kwargs)

        
        self.add_parameter(
            name='gain',
            label='Gain',
            unit='A/V',
            get_cmd='GAIN?',
            set_cmd='GAIN {:d}',
            get_parser=self._get_gain,
            set_parser=self._set_gain,
            )

        self.add_parameter(
            name='input',
            label='Analog input',
            get_cmd='INPT?',
            set_cmd='INPT{:d}',
            vals=Ints(0,1),
        )

        self.add_parameter(
            name='speed',
            label='Speed',
            get_cmd='RESP?',
            set_cmd='RESP{:d}',
            val_mapping={
                'fast': 0,
                'slow': 1},
            vals=Ints(0,1)
        )

        self.add_parameter(
            name='shield',
            label='Inner shield',
            get_cmd='SHLD?',
            set_cmd='SHLD{:d}',
            val_mapping={
                'guard': 0,
                'return': 1},
            vals=Ints(0,1)
        )

        self.add_parameter(
            name='isolation',
            label='Isolation',
            get_cmd='ISOL?',
            set_cmd='ISOL{:d}',
            val_mapping={
                'ground': 0,
                'float': 1},
            vals=Ints(0, 1)
        )

        self.add_parameter(
            name='output',
            label='Output',
            get_cmd='SOUT?',
            set_cmd='SOUT{:d}',
            val_mapping={
                'off': 0,
                'on': 1},
            vals=Ints(0,1),
        )

        self.add_parameter(
            name='current',
            label='DC current',
            unit='A',
            get_cmd='CURR?',
            set_cmd='CURR{:e}',
            vals=Numbers(min_value=-100e-3,max_value=100e-3),
        )

        self.add_parameter(
            name='voltage',
            label='Compliance voltage',
            unit='V',
            get_cmd='VOLT?',
            set_cmd='VOLT{:f}',
            vals=Numbers(min_value=0.0, max_value=50.0),
        )

        self.add_parameter(
            name='alarm',
            label='Audible alarms',
            get_cmd='ALRM?',
            set_cmd='ALRM{:d}',
            val_mapping={
                'off': 0,
                'on': 1},
            vals=Ints(0,1),
        )

        self.connect_message()



    def get_idn(self) -> Dict[str, Optional[str]]:
        """ Return the Instrument Identifier Message """
        idstr = self.ask('*IDN?')
        idparts = [p.strip() for p in idstr.split(',', 4)][1:]

        return dict(zip(('vendor', 'model, serial', 'firmware'), idparts))

    def _reset(self):
        """Reset the CS580 to its default configuration"""
        self.write('*RST')

    def get_overload(self) -> str:
        """ Reads the current avlue of the signal overload status."""
        id = self.ask('OVLD?')
        if isstr(id):
            return id
        elif id == 1:
            return "Compliance limit reached"
        elif id == 2:
            return "Analog input overload"
        elif id == 3:
            return "Compliance limit reached and Analog input overload"
        else:
            return "NONE"

    def _get_gain(self, s: int) -> float:
        return self._n_to_gains[int(s)]

    def _set_gain(self, s: float) -> int:
        return self._gains[s]