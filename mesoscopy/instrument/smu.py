"""
functions related to the Source-Measurement Units.
Works with Keithley 2600 and 2400 family.
"""

from ..measurement import fastsweep
from typing import Optional, Sequence, Any, List
from time import sleep
from qcodes import Station, Instrument, Parameter
from qcodes.instrument import InstrumentChannel

from qcodes.instrument_drivers.tektronix.Keithley_2600_channels import (
    KeithleyChannel, Keithley_2600)
from  qcodes.instrument_drivers.tektronix.Keithley_2450 import (Keithley2450, Source2450)
from qcodes_contrib_drivers.drivers.StanfordResearchSystems.SIM928 import SIM928



# Classes to add a "max_rate" parameter to the Keithley channels

class Keithley2600Channel(KeithleyChannel):
    def __init__(self, parent: Instrument, name: str, channel: str) -> None:
        super().__init__(parent, name, channel)

        self.max_rate = Parameter(
            'max_rate',
            unit='V/s or A/s',
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

class Keithley2400Source(Source2450):
    def __init__(self, parent: "Keithley2450", name:str, proper_function:str, **kwargs: Any) -> None:
        super().__init__(parent, name, proper_function, **kwargs)

        #self.function = self.parent.source_function
        #
        #self.add_parameter()
    
class Keithley2400(Keithley2450):
    def __init__(self, name: str, address: str, **kwargs: Any) -> None:
        super().__init__(name, address, **kwargs)

        self.add_parameter(
            'max_rate',
            unit='V/s or A/s',
            get_cmd = None,
            set_cmd = None,
            label='maximum sweeping rate',
            initial_value=0
        )
    
class SRS_SIM928(SIM928):
    def __init__(self,
                 name: str,
                 address: str,
                 slot_names=None,
                 **kwargs) -> None:
        super().__init__(name, address, slot_names, **kwargs)

        # TODO: rewrite SIM928 as an InstrumetChannel of SIM900, so that the
        # max_rate parameter can be applied independently on different channels.

        self.max_rate = Parameter(
            'max_rate',
            unit='V/s',
            get_cmd=None,
            set_cmd=None,
            label='maximum sweeping rate',
            instrument=self,
            initial_value=0
        )


# functions to initialise the keithleys with the max sweep parameters and
# voltage compliance limits

def init_smu(
    station: Station,
    mode: Optional[Sequence[str]] = ['voltage', 'voltage'],
    limits_v: Optional[Sequence[float]] = [20, 70],
    max_rate: Optional[Sequence[float]] = [0.05, 0.1],
    limits_i: Optional[Sequence[float]] = [1e-8, 5e-8]
):

    keithleys2600 = []
    keithleys2400 = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == Keithley2600:
                keithleys2600.append(name)
            elif itm.__class__ == Keithley2400:
                keithleys2400.append(name)

    item = 0
    for instr in keithleys2600:
        if mode[item] == 'voltage':
            if station.__getattr__(instr).smua.output() == 'off':
                station.__getattr__(instr).smua.volt(0)
                station.__getattr__(instr).smua.curr(0)
            elif station.__getattr__(instr).smua.mode() == 'current' and station.__getattr__(instr).smua.curr() != 0:
                fastsweep(0, station.__getattr__(instr).smua.curr)
            station.__getattr__(instr).smua.max_rate(max_rate[item])
            station.__getattr__(instr).smua.mode('voltage')
            station.__getattr__(instr).smua.nplc(0.05)
            if limits_v[item] <= .2:
                station.__getattr__(instr).smua.sourcerange_v(.2)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).smua.sourcerange_v(2)
            elif limits_v[item] <= 20:
                station.__getatttr__(instr).smua.sourcerange_v(20)
            else:
                station.__getattr__(instr).smua.sourcerange_v(200)
            station.__getattr__(instr).smua.limitv(limits_v[item])
            if limits_i[item] <= 1e-7:
                station.__getattr__(instr).smub.measurerange_i(1e-7)
            elif limits_i[item] <= 1e-6:
                station.__getattr__(instr).smub.measurerange_i(1e-6)
            elif limits_i[item] <= 1e-5:
                station.__getattr__(instr).smub.measurerange_i(1e-5)
            elif limits_i[item] <= 1e-4:
                station.__getattr__(instr).smub.measurerange_i(1e-4)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).smub.measurerange_i(1e-3)
            elif limits_i[item] <= 1e-2:
                station.__getattr__(instr).smub.measurerange_i(1e-2)
            elif limits_i[item] <= 1:
                station.__getattr__(instr).smub.measurerange_i(1)
            else:
                station.__getattr__(instr).smub.measurerange_i(1.5)
            station.__getattr__(instr).smua.limiti(limits_i[item])
            station.__getattr__(instr).smua.output('on')

            print(
                f'{instr} smua channel sourcing voltage: limit {limits_v[item]} V, max sweep rate: '
                f'{max_rate[item]}, current limit {limits_i[item]} A.\n')

        elif mode[item] == 'current':
            if station.__getattr__(instr).smua.output() == 'off':
                station.__getattr__(instr).smua.volt(0)
                station.__getattr__(instr).smua.curr(0)
            elif station.__getattr__(instr).smua.mode() == 'voltage' and station.__getattr__(instr).smua.curr() !=0:
                fastsweep(0, station.__getattr__(instr).smua.volt)
            station.__getattr__(instr).smua.max_rate(max_rate[item])
            station.__getattr__(instr).smua.mode('current')
            station.__getattr__(instr).smua.nplc(0.05)
            if limits_i[item] <= 1e-7:
                station.__getattr__(instr).smua.sourcerange_i(1e-7)
            elif limits_i[item] <= 1e-6:
                station.__getattr__(instr).smua.sourcerange_i(1e-6)
            elif limits_i[item] <= 1e-5:
                station.__getattr__(instr).smua.sourcerange_i(1e-5)
            elif limits_i[item] <= 1e-4:
                station.__getattr__(instr).smua.sourcerange_i(1e-4)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).smua.sourcerange_i(1e-3)
            elif limits_i[item] <= 1e-2:
                station.__getattr__(instr).smua.sourcerange_i(1e-2)
            elif limits_i[item] <= 1:
                station.__getattr__(instr).smua.sourcerange_i(1)
            else:
                station.__getattr__(instr).smua.sourcerange_i(1.5)
            station.__getattr__(instr).smua.limiti(limits_i[item])
            if limits_v[item] <= .2:
                station.__getattr__(instr).smua.measurerange_v(.2)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).smua.measurerange_v(2)
            elif limits_v[item] <= 20:
                station.__getatttr__(instr).smua.measurerange_v(20)
            else:
                station.__getattr__(instr).smua.measurerange_v(200)
            station.__getattr__(instr).smua.limitv(limits_v[item])
            station.__getattr__(instr).smua.output('on')
            print(
                f'{instr} smua channel sourcing current: limit {limits_i[item]} A, max sweep rate: '
                f'{max_rate[item]}, voltage limit {limits_v[item]} V.\n')

        else:
            print(f'smua mode on {station.__getattr__(instr).name} is invalid.\n Please use either ```current``` or ```voltage```.\n')

        item += 1
        
        if mode[item] == 'voltage':
            if station.__getattr__(instr).smub.output() == 'off':
                station.__getattr__(instr).smub.volt(0)
                station.__getattr__(instr).smub.curr(0)
            elif station.__getattr__(instr).smua.mode() == 'current' and station.__getattr__(instr).smua.curr() != 0:
                fastsweep(0, station.__getattr__(instr).smua.curr)
            station.__getattr__(instr).smub.mode('voltage')
            station.__getattr__(instr).smub.nplc(0.05)
            if limits_v[item] <= .2:
                station.__getattr__(instr).smub.sourcerange_v(.2)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).smub.sourcerange_v(2)
            elif limits_v[item] <= 20:
                station.__getatttr__(instr).smub.sourcerange_v(20)
            else:
                station.__getattr__(instr).smub.sourcerange_v(200)
            station.__getattr__(instr).smub.limitv(limits_v[item])
            if limits_i[item] <= 1e-7:
                station.__getattr__(instr).smub.measurerange_i(1e-7)
            elif limits_i[item] <= 1e-6:
                station.__getattr__(instr).smub.measurerange_i(1e-6)
            elif limits_i[item] <= 1e-5:
                station.__getattr__(instr).smub.measurerange_i(1e-5)
            elif limits_i[item] <= 1e-4:
                station.__getattr__(instr).smub.measurerange_i(1e-4)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).smub.measurerange_i(1e-3)
            elif limits_i[item] <= 1e-2:
                station.__getattr__(instr).smub.measurerange_i(1e-2)
            elif limits_i[item] <= 1:
                station.__getattr__(instr).smub.measurerange_i(1)
            else:
                station.__getattr__(instr).smub.measurerange_i(1.5)
            station.__getattr__(instr).smub.limiti(limits_i[item])
            station.__getattr__(instr).smub.output('on')
            station.__getattr__(instr).smub.max_rate(max_rate[item])

            print(f'{instr} smub channel sourcing voltage: limit {limits_v[item]}, max sweep rate: '
                f'{max_rate[item]}. current limit {limits_i[item]}\n')
            item += 1
        elif mode[item] == 'current':
            if station.__getattr__(instr).smua.output() == 'off':
                station.__getattr__(instr).smua.volt(0)
                station.__getattr__(instr).smua.curr(0)
            elif station.__getattr__(instr).smua.mode() == 'voltage' and station.__getattr__(instr).smua.volt() != 0:
                fastsweep(0, station.__getattr__(instr).smua.volt)
            station.__getattr__(instr).smub.max_rate(max_rate[item])
            station.__getattr__(instr).smub.mode('current')
            station.__getattr__(instr).smub.nplc(0.05)
            if limits_i[item] <= 1e-7:
                station.__getattr__(instr).smub.sourcerange_i(1e-7)
            elif limits_i[item] <= 1e-6:
                station.__getattr__(instr).smub.sourcerange_i(1e-6)
            elif limits_i[item] <= 1e-5:
                station.__getattr__(instr).smub.sourcerange_i(1e-5)
            elif limits_i[item] <= 1e-4:
                station.__getattr__(instr).smub.sourcerange_i(1e-4)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).smub.sourcerange_i(1e-3)
            elif limits_i[item] <= 1e-2:
                station.__getattr__(instr).smub.sourcerange_i(1e-2)
            elif limits_i[item] <= 1:
                station.__getattr__(instr).smub.sourcerange_i(1)
            else:
                station.__getattr__(instr).smub.sourcerange_i(1.5)
            station.__getattr__(instr).smub.limiti(limits_i[item])
            if limits_v[item] <= .2:
                station.__getattr__(instr).smub.measurerange_v(.2)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).smub.measurerange_v(2)
            elif limits_v[item] <= 20:
                station.__getatttr__(instr).smub.measurerange_v(20)
            else:
                station.__getattr__(instr).smub.measurerange_v(200)
            station.__getattr__(instr).smub.limitv(limits_v[item])
            station.__getattr__(instr).smub.output('on')
            print(f'{instr} smub channel sourcing current: limit {limits_i[item]} A, max sweep rate: '
                f'{max_rate[item]}, voltage limit {limits_v[item]} V.\n')

        else:
            print(f'smub mode on {station.__getattr__(instr).name} is invalid.\n Please use either ```current``` or ```voltage```.')

    for instr in keithleys2400:
        if mode[item] == 'voltage':
            station.__getattr__(instr).source.function('voltage')
            station.__getattr__(instr).source.user_number(1)
            station.__getattr__(instr).sense.user_number(1)
            if not station.__getattr__(instr).output_enabled():
                station.__getattr__(instr).source.voltage(0)
            if limits_v[item] <= 20e-3:
                station.__getattr__(instr).source.range(20e-3)
            elif limits_v[item] <= 200e-3:
                station.__getattr__(instr).source.range(200e-3)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).source.range(2)
            elif limits_v[item] <= 20:
                station.__getattr__(instr).source.range(20)
            else:
                station.__getattr__(instr).source.range(200)

            station.__getattr__(instr).sense.function('current')
            station.__getattr__(instr).sense.four_wire_measurement(False)

            if limits_i[item] <= 10e-9:
                station.__getattr__(instr).sense.range(10e-9)
            elif limits_i[item] <= 100e-9:
                station.__getattr__(instr).sense.range(100e-9)
            elif limits_i[item] <= 1e-6:
                station.__getattr__(instr).sense.range(1e-6)
            elif limits_i[item] <= 10e-6:
                station.__getattr__(instr).sense.range(10e-6)
            elif limits_i[item] <= 100e-6:
                station.__getattr__(instr).sense.range(100e-6)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).sense.range(1e-3)
            elif limits_i[item] <= 10e-3:
                station.__getattr__(instr).sense.range(10e-3)
            elif limits_i[item] <= 100e-3:
                station.__getattr__(instr).sense.range(100e-3)
            else:
                station.__getattr__(instr).sense.range(1)
            station.__getattr__(instr).source.limit(limits_i[item])
            sleep(1)
            station.__getattr__(instr).output_enabled(True)
            sleep(1)
            station.__getattr__(instr).max_rate(max_rate[item])

            print(f'{instr} sourcing voltage: limit {limits_v[item]}, max sweep rate: '
                f'{max_rate[item]}.\n')

        elif mode[item] == 'current':
            station.__getattr__(instr).source.function('current')
            station.__getattr__(instr).source.user_number(1)
            station.__getattr__(instr).sense.user_number(1)
            if not station.__getattr__(instr).output_enabled():
                station.__getattr__(instr).source.current(0)
            if limits_i[item] <= 1e-6:
                station.__getattr__(instr).source.range(1e-6)
            elif limits_i[item] <= 10e-6:
                station.__getattr__(instr).source.range(10e-6)
            elif limits_i[item] <= 100e-6:
                station.__getattr__(instr).source.range(100e-6)
            elif limits_i[item] <= 1e-3:
                station.__getattr__(instr).source.range(1e-3)
            elif limits_i[item] <= 10e-3:
                station.__getattr__(instr).source.range(10e-3)
            elif limits_i[item] <= 100e-3:
                station.__getattr__(instr).source.range(100e-3)
            elif limits_i[item] <= 1:
                station.__getattr__(instr).source.range(1)
            elif limits_i[item] <= 4:
                station.__getattr__(instr).source.range(4)
            elif limits_i[item] <=5:
                station.__getattr__(instr).source.range(5)
            elif limits_i[item] <=7:
                station.__getattr__(instr).source.range(7)
            else:
                station.__getattr__(instr).source.range(10)

            station.__getattr__(instr).sense.function('voltage')
            station.__getattr__(instr).sense.four_wire_measurement(False)
            if limits_v[item] <= 200e-3:
                station.__getattr__(instr).sense.range(20e-3)
            elif limits_v[item] <= 2:
                station.__getattr__(instr).sense.range(2)
            elif limits_v[item] <= 7:
                station.__getattr__(instr).sense.range(7)
            elif limits_v[item] <= 10:
                station.__getattr__(instr).sense.range(10)
            elif limits_v[item] <= 20:
                station.__getattr__(instr).sense.range(20)
            else:
                station.__getattr__(instr).sense.range(100)
            station.__getattr__(instr).source.limit(limits_v[item])
            sleep(1)
            station.__getattr__(instr).output_enabled(True)
            sleep(1)
            station.__getattr__(instr).max_rate(max_rate[item])

            print(f'{instr} sourcing current: limit {limits_i[item]}, max sweep rate: '
                f'{max_rate[item]}.\n')

        item += 1

def init_sim928(
    station: Station,
    max_rate: Optional[float] = 0.15,
):
    sim900 = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == SRS_SIM928:
                sim900.append(name)

    for instr in sim900:
        station.__getattr__(instr).max_rate(max_rate)

        print(f'{instr}: max sweep rate: {max_rate}.\n')
