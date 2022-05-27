"""
some initialisation functions for experiments
"""

from typing import Optional
from qcodes import Station, Instrument
from numpy import pi

import zhinst.qcodes
from qcodes.instrument_drivers.stanford_research import SR830


def init_lockin(
    station: Station,
    freq: Optional[float] = 127,
    ampl: Optional[float] = 1,
    TC: Optional[float] = None,
):
    """container for initialise mfli and SR830 all at once"""
    mfli = False
    if _list_mflis(station):
        mfli = True

    init_mfli(
        station,
        freq=freq,
        ampl=ampl,
        TC=TC)
    init_sr830(
        station,
        mfli=mfli,
        freq=freq,
        TC=TC)
    autorange_sr830(station)


def init_mfli(
    station: Station,
    freq: Optional[float] = 127,
    ampl: Optional[float] = 1,
    TC: Optional[float] = None,
    filterorder: Optional[int] = 8,
    sensitivity: Optional[float] = 0.003
):

    mflis = _list_mflis(station)

    if TC:
        timeconst = TC
    else:
        timeconst = 100/freq/2/pi

    station.__getattr__(mflis[0]).oscs[0].freq(freq)
    station.__getattr__(mflis[0]).sigouts[0].on(1)
    station.__getattr__(mflis[0]).sigouts[0].range(10)
    station.__getattr__(mflis[0]).sigouts[0].amplitudes0(ampl*2**(1/2))
    station.__getattr__(mflis[0]).sigouts[0].enables0(1)
    station.__getattr__(mflis[0]).sigouts[0].enables1(0)
    station.__getattr__(mflis[0]).sigouts[0].imp50(0)
    station.__getattr__(mflis[0]).sigouts[0].offset(0)
    station.__getattr__(mflis[0]).sigouts[0].diff(0)
    station.__getattr__(mflis[0]).triggers.out[0].source(52)
    station.__getattr__(mflis[0]).triggers.out[1].source(1)
    station.__getattr__(mflis[0]).demods[3].oscselect(0)
    station.__getattr__(mflis[0]).demods[3].adcselect(1)
    station.__getattr__(mflis[0]).demods[3].sinc(1)

    for mfli in mflis[1:]:
        station.__getattr__(mfli).demods[1].adcselect(3)
        station.__getattr__(mfli).demods[0].adcselect(0)
        station.__getattr__(mfli).extrefs[0].enable(1)
        station.__getattr__(mfli).sigouts[0].on(0)
        station.__getattr__(mfli).triggers.out[0].source(0)
        station.__getattr__(mfli).triggers.out[1].source(0)

    for mfli in mflis:
        station.__getattr__(mfli).demods[0].oscselect(0)
        station.__getattr__(mfli).demods[0].harmonic(1)
        station.__getattr__(mfli).demods[0].phaseshift(0)
        station.__getattr__(mfli).demods[0].sinc(1)
        station.__getattr__(mfli).demods[0].timeconstant(timeconst)
        station.__getattr__(mfli).demods[0].order(filterorder)

        station.__getattr__(mfli).sigins[0].ac(1)
        station.__getattr__(mfli).sigins[0].imp50(0)
        station.__getattr__(mfli).sigins[0].diff(1)
        station.__getattr__(mfli).sigins[0].float(1)
        station.__getattr__(mfli).sigins[0].scaling(1)
        station.__getattr__(mfli).sigins[0].range(sensitivity)

        station.__getattr__(mfli).sigouts[0].range(10)

    print(f'Lock-in {mflis[0]} sources the reference signal with f={freq}Hz\n'
          f'time constant: {timeconst}s.\n'
          f'Output voltage: {ampl}V.\n\n'
          f'Lock-ins {mflis[1:]} have the following frequencies:\n'
          )
    for mfli in mflis[1:]:
        print(mfli, ": ", station.__getattr__(mfli).oscs[0].freq())

    return


def init_sr830(
    station: Station,
    mfli=False,
    freq: Optional[float] = 127,
    ampl: Optional[float] = 1,
    TC: Optional[float] = None,
    filter: Optional[bool] = True,
    sensitivity: Optional[float] = 20e-6,
    phase: Optional[float] = 0,
):
    sr830s = _list_sr830(station)

    if TC:
        timeconst = TC
    else:
        timeconst = 100/freq/2/pi

    if mfli:  # in that case, we lock everything on the first mfli
        mflis = _list_mflis(station)
        timeconst = station.__getattr__(mflis[0]).demods[0].timeconstant()

        station.__getattr__(sr830s[0]).reference_source('external')
    else:
        station.__getattr__(sr830s[0]).reference_source('internal')
        station.__getattr__(sr830s[0]).amplitude(ampl*2**(1/2))
        station.__getattr__(sr830s[0]).frequency(freq)

    for sr830 in sr830s:
        station.__getattr__(sr830).time_constant(timeconst)
        station.__getattr__(sr830).harmonic(1)
        station.__getattr__(sr830).input_config('a-b')
        station.__getattr__(sr830).input_shield('float')
        station.__getattr__(sr830).input_coupling('DC')
        station.__getattr__(sr830).phase(phase)
        station.__getattr__(sr830).sensitivity(sensitivity)

        if filter:
            station.__getattr__(sr830).notch_filter('both')
            station.__getattr__(sr830).sync_filter('on')
            station.__getattr__(sr830).filter_slope(18)
        else:
            station.__getattr__(sr830).notch_filter('off')
            station.__getattr__(sr830).sync_filter('off')

        station.__getattr__(sr830).auto_reserve()

    for sr830 in sr830s[1:]:
        station.__getattr__(sr830).reference_source('external')


def enable_DC(station: Station):
    mflis = _list_mflis(station)
    for mfli in mflis:
        station.__getattr__(mfli).oscs[1].freq(0)
        station.__getattr__(mfli).demods[2].adcselect(0)
        station.__getattr__(mfli).demods[2].oscselect(1)
        station.__getattr__(mfli).demods[2].harmonic(1)
        station.__getattr__(mfli).demods[2].phaseshift(0)
        station.__getattr__(mfli).demods[2].sinc(0)
        station.__getattr__(mfli).demods[2].timeconstant(.1)
        station.__getattr__(mfli).demods[2].order(3)
        station.__getattr__(mfli).sigins[0].ac(0)
    print(f'DC enabled for {mflis}')


def disable_DC(station: Station):
    mflis = _list_mflis(station)
    for mfli in mflis:
        station.__getattr__(mfli).sigins[0].ac(1)
    print(f'DC disabled for {mflis}')


def measure_diff(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).sigins[0].diff(1)
        print(f'measure A-B diff signal for {mflis}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).input_config('a-b')
        print(f'measure A-B diff signal for {sr830s}')
    else:
        print('no lockin found')


def autorange_sr830(station: Station, max_changes=4):
    """ function to autorange al SR830 lockin amplifiers at once.

    Args:
        station: Station
        max_changes: int between 1 and 26
    """
    sr830s = _list_sr830(station)
    for sr830 in sr830s:
        station.__getattr__(sr830).autorange(max_changes=max_changes)
        sens = station.__getattr__(sr830).sensitivity()
        print(f'{sr830} set to {sens}')


def filterslope_sr830(station: Station, filterslope=18):
    sr830s = _list_sr830(station)
    for sr830 in sr830s:
        station.__getattr__(sr830).filter_slope(filterslope)
        print(f'{sr830} set to {filterslope} dB/oct')


def change_TC(station: Station, timeconst):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).demods[0].timeconstant(timeconst)
        print(f'TC changed to {timeconst} for {mflis}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).time_constant(timeconst)
        print(f'TC changed to {timeconst} for {sr830s}')
    else:
        print('no lockin found')


def enable_sinc(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).demods[0].sinc(1)
        print(f'SINC filter enabled for {mflis}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).sync_filter('on')
        print(f'SINC filter enabled for {sr830}')


def disable_sinc(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).demods[0].sinc(0)
        print(f'SINC filter disabled for {mflis}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).sync_filter('off')
        print(f'SINC filter disabled for {sr830}')


def measure_single_ended(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).sigins[0].diff(0)
        print(f'measure single end A signal for {mflis}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).input_config('a')
        print(f'measure single end A signal for {sr830s}')
    else:
        print('no lockin found')


def _list_mflis(station: Station):
    mflis = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                mflis.append(name)
    return mflis


def _list_sr830(station: Station):
    sr830s = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == SR830.SR830:  # TODO: check if bug
                sr830s.append(name)
    return sr830s


def _is_DC(station: Station):
    mfli = _list_mflis(station)[0]
    return not station.__getattr__(mfli).sigins[0].ac()
    # TODO: check that this works in real life
