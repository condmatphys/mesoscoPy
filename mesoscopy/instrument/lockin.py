"""
some initialisation functions for experiments
"""

from typing import Optional
from qcodes import Station, Instrument

import zhinst.qcodes


def initialise_lockin(station: Station,
                      freq: Optional[float] = 127,
                      ampl: Optional[float] = 1):

    lockins = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                lockins.append(name)

    station.__getattr__(lockins[0]).oscs[0].freq(freq)
    station.__getattr__(lockins[0]).sigouts[0].on(1)
    station.__getattr__(lockins[0]).sigouts[0].range(10)
    station.__getattr__(lockins[0]).sigouts[0].amplitudes0(ampl*2**(1/2))
    station.__getattr__(lockins[0]).sigouts[0].enables0(1)
    station.__getattr__(lockins[0]).sigouts[0].enables1(0)
    station.__getattr__(lockins[0]).sigouts[0].imp50(0)
    station.__getattr__(lockins[0]).sigouts[0].offset(0)
    station.__getattr__(lockins[0]).sigouts[0].diff(0)
    station.__getattr__(lockins[0]).triggers.out[0].source(52)
    station.__getattr__(lockins[0]).triggers.out[1].source(1)
    station.__getattr__(lockins[0]).demods[3].oscselect(0)
    station.__getattr__(lockins[0]).demods[3].adcselect(1)
    station.__getattr__(lockins[0]).demods[3].sinc(1)
    station.__getattr__(lockins[0]).demods[3].timeconstant(.1)
    station.__getattr__(lockins[0]).demods[3].order(8)

    for lockin in lockins[1:]:
        station.__getattr__(lockin).demods[0].adcselect(3)
        station.__getattr__(lockin).extrefs[0].enable(1)
        station.__getattr__(lockin).sigouts[0].on(0)
        station.__getattr__(lockin).triggers.out[0].source(0)
        station.__getattr__(lockin).triggers.out[1].source(0)

    for lockin in lockins:
        station.__getattr__(lockin).demods[0].oscselect(0)
        station.__getattr__(lockin).demods[0].harmonic(1)
        station.__getattr__(lockin).demods[0].phaseshift(0)
        station.__getattr__(lockin).demods[0].sinc(1)
        station.__getattr__(lockin).demods[0].timeconstant(.1)
        station.__getattr__(lockin).demods[0].order(8)

        station.__getattr__(lockin).sigins[0].ac(1)
        station.__getattr__(lockin).sigins[0].imp50(0)
        station.__getattr__(lockin).sigins[0].diff(1)
        station.__getattr__(lockin).sigins[0].float(0)
        station.__getattr__(lockin).sigins[0].scaling(1)
        station.__getattr__(lockin).sigins[0].range(3e-3)

        station.__getattr__(lockin).sigouts[0].range(10)

    print(f'Lock-in {lockins[0]} sources the reference signal with f={freq}Hz\n'
          f'Output voltage: {ampl}V.\n\n'
          f'Lock-ins {lockins[1:]} have the following frequencies:\n'
          )
    for lockin in lockins[1:]:
        print(lockin, ": ", station.__getattr__(lockin).oscs[0].freq())

    return


def enable_DC(station: Station):
    lockins = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                lockins.append(name)

    for lockin in lockins:
        station.__getattr__(lockin).oscs[1].freq(0)
        station.__getattr__(lockin).demods[2].adcselect(0)
        station.__getattr__(lockin).demods[2].oscselect(1)
        station.__getattr__(lockin).demods[2].harmonic(1)
        station.__getattr__(lockin).demods[2].phaseshift(0)
        station.__getattr__(lockin).demods[2].sinc(0)
        station.__getattr__(lockin).demods[2].timeconstant(.1)
        station.__getattr__(lockin).demods[2].order(3)
        station.__getattr__(lockin).sigins[0].ac(0)
    print(f'DC enabled for {lockins}')


def disable_DC(station: Station):
    lockins = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                lockins.append(name)

    for lockin in lockins:
        station.__getattr__(lockin).sigins[0].ac(1)
    print(f'DC disabled for {lockins}')
