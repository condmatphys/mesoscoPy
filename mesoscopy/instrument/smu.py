"""
functions related to the Source-Measurement Units.
Works with Keithley 2600 and 2400 family.
"""

from typing import Optional, Sequence, Any, List
from qcodes import Station, Instrument, Parameter

from qcodes.instrument_drivers.tektronix.Keithley_2600_channels import (
    KeithleyChannel, Keithley_2600)
import qcodes.instrument_drivers.tektronix.Keithley_2400
import qcodes.instrument_drivers.tektronix.Keithley_2450


# Classes to add a "max_rate" parameter to the Keithley channels

class Keithley2600Channel(KeithleyChannel):
    def __init__(self, parent: Instrument, name: str, channel: str) -> None:
        super().__init__(parent, name, channel)

        self.max_rate = Parameter(
            'max_rate',
            unit='V/s',
            get_cmd=None,
            set_cmd=None,
            label='maximum sweeping rate',
            instrument=self,
            initial_value=0
        )


class Keithley2600(Keithley_2600):
    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, **kwargs)

        self.channels: List[Keithley2600Channel] = []
        for ch in ['a', 'b']:
            ch_name = f'smu{ch}'
            channel = Keithley2600Channel(self, ch_name, ch_name)
            self.submodules[ch_name] = (channel)
            self.channels.append(channel)


# functions to initialise the keithleys with the max sweep parameters and
# voltage compliance limits

def init_smu(
    station: Station,
    limits_v: Optional[Sequence[float]] = [20, 70],
    max_rate: Optional[Sequence[float]] = [0.05, 0.1]
):

    keithleys2600 = []
    keithleys2400 = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == Keithley2600:
                keithleys2600.append(name)
            elif itm.__class__ == (
                qcodes.instrument_drivers.tektronix.Keithley_2400.Keithley_2400
                or
                qcodes.instrument_drivers.tektronix.Keithley_2450.Keithley_2450
            ):
                keithleys2400.append(name)

    item = 0
    for instr in keithleys2600:
        if station.__getattr__(instr).smua.output() == 'off':
            station.__getattr__(instr).smua.volt(0)
            station.__getattr__(instr).smua.curr(0)
        station.__getattr__(instr).smua.mode('voltage')
        station.__getattr__(instr).smua.nplc(0.05)
        station.__getattr__(instr).smua.sourcerange_v(20)
        station.__getattr__(instr).smua.limitv(limits_v[item])
        station.__getattr__(instr).smua.measurerange_i(1e-7)
        station.__getattr__(instr).smua.limiti(1e-8)
        station.__getattr__(instr).smua.output('on')
        station.__getattr__(instr).smua.max_rate(max_rate[item])

        print(f'{instr} smua channel: limit {limits_v[item]}, max sweep rate: '
              f'{max_rate[item]}.\n')
        item += 1

        if station.__getattr__(instr).smub.output() == 'off':
            station.__getattr__(instr).smub.volt(0)
            station.__getattr__(instr).smub.curr(0)
        station.__getattr__(instr).smub.mode('voltage')
        station.__getattr__(instr).smub.nplc(0.05)
        station.__getattr__(instr).smub.sourcerange_v(200)
        station.__getattr__(instr).smub.limitv(limits_v[item])
        station.__getattr__(instr).smub.measurerange_i(1e-7)
        station.__getattr__(instr).smub.limiti(1e-8)
        station.__getattr__(instr).smub.output('on')
        station.__getattr__(instr).smub.max_rate(max_rate[item])

        print(f'{instr} smub channel: limit {limits_v[item]}, max sweep rate: '
              f'{max_rate[item]}.\n')
        item += 1

    for instr in keithleys2400:
        if not station.__getattr__(instr).output_enabled():
            station.__getattr__(instr).source.voltage(0)
            station.__getattr__(instr).source.current(0)
        station.__getattr__(instr).source.function('voltage')
        if limits_v[item] < 20:
            station.__getattr__(instr).source.range(20)
        else:
            station.__getattr__(instr).source.range(200)
        station.__getattr__(instr).source.limit(limits_v[item])

        station.__getattr__(instr).sense.function('current')
        station.__getattr__(instr).sense.four_wire_measurement(False)
        station.__getattr__(instr).sense.range(1e-7)
        station.__getattr__(instr).sense.limit(1e-8)
        station.__getattr__(instr).sense.output_enabled(True)
        station.__getattr__(instr).source.__dict__['max_rate'] = max_rate[item]

        print(f'{instr}: limit {limits_v[item]}, max sweep rate: '
              f'{max_rate[item]}.\n')

    return
