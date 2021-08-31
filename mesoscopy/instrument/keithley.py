"""
some initialisation functions for experiments
"""

from typing import Optional, Sequence
from qcodes import Station, Instrument

import qcodes.instrument_drivers.tektronix.Keithley_2600_channels.Keithley_2600
import qcodes.instrument_drivers.tektronix.Keithley_2400.Keithley2400
import qcodes.instrument_drivers.tektronix.Keithley_2450.Keithley2450


def initialise_keithley(station: Station,
                        limits_v: Optional[Sequence[float]] = [20, 70],
                        ):

    keithleys2600 = []
    keithleys2400 = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == qcodes.instrument_drivers.tektronix.Keithley_2600_channels.Keithley_2600:
                keithleys2600.append(name)
            elif itm.__class__ == (
                qcodes.instrument_drivers.tektronix.Keithley_2400.Keithley2400
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
        item += 1

        print(f'{instr} is set up. limits are {limits_v[item-1]} (smua) and'
              f'{limits_v[item]} (smub)\n')

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

        print(f'{instr} is set up, with voltage limit {limits_v[item]}.\n')

    return
