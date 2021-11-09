from typing import Any

from qcodes import VisaInstrument, validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping


class RohdeSchwarz_SMB100A(VisaInstrument):
    """
    driver for the Rohde & Schwarz SMB100A RF Source.

    TODO: add modulation subsystem.

    """

    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, terminator='\n', **kwargs)

        self.add_parameter(name='frequency',
                           label='Frequency',
                           unit='Hz',
                           get_cmd='SOUR:FREQ?',
                           set_cmd='SOUR:FREQ {:.2f}',
                           get_parser=float,
                           vals=vals.Numbers(1e6, 20e9))
        self.add_parameter(name='phase',
                           label='Phase',
                           unit='deg',
                           get_cmd='SOUR:PHAS?',
                           set_cmd='SOUR:PHAS {:.2f}',
                           get_parser=float,
                           vals=vals.Numbers(0, 360))
        self.add_parameter(name='power',
                           label='Power',
                           unit='dBm',
                           get_cmd='SOUR:POW?',
                           set_cmd='SOUR:POW {:.2f}',
                           get_parser=float,
                           vals=vals.Numbers(-120, 25))
        self.add_parameter('status',
                           label='RF Output',
                           get_cmd=':OUTP:STAT?',
                           set_cmd=':OUTP:STAT {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))
        self.add_parameter('pulsemod_state',
                           label='Pulse Modulation',
                           get_cmd=':SOUR:PULM:STAT?',
                           set_cmd=':SOUR:PULM:STAT {}',
                           val_mapping=create_on_off_val_mapping(on_val='1',
                                                                 off_val='0'))
        self.add_function('reset', call_cmd='*RST')
        self.add_function('run_self_tests', call_cmd='*TST?')

        self.connect_message()

    def on(self) -> None:
        self.status('on')

    def off(self) -> None:
        self.status('off')
