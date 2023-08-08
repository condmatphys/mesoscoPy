"""
some initialisation functions for experiments
"""

from typing import Optional
from qcodes import Station, Instrument, Parameter
from numpy import pi

import zhinst.qcodes
from zhinst.qcodes import MFLI
from qcodes.instrument_drivers.stanford_research import SR830, SR860
from qcodes.utils.validators import Any, ComplexNumbers
from qcodes.instrument.parameter import ParamRawDataType


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
    if _list_sr860(station):
        sr860 = True

    init_mfli(
        station,
        freq=freq,
        ampl=ampl,
        TC=TC)
    init_sr860(
        station,
        mfli=mfli,
        freq=freq,
        TC=TC)
    init_sr830(
        station,
        mfli=mfli,
        sr860=sr860,
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
    amplitude = ampl * 2 ** (1/2)

    if TC:
        timeconst = TC
    else:
        timeconst = 100/freq/2/pi

    station.__getattr__(mflis[0]).oscs[0].freq(freq)
    station.__getattr__(mflis[0]).sigouts[0].on(1)
    if amplitude <= .01:
        station.__getattr__(mflis[0]).sigouts[0].range(.01)
    elif amplitude <= .1:
        station.__getattr__(mflis[0]).sigouts[0].range(.1)
    elif amplitude <= 1:
        station.__getattr__(mflis[0]).sigouts[0].range(1)
    else:
        station.__getattr__(mflis[0]).sigouts[0].range(10)
    station.__getattr__(mflis[0]).sigouts[0].amplitudes[0].value(amplitude)
    station.__getattr__(mflis[0]).sigouts[0].enables[0].value(1)
    station.__getattr__(mflis[0]).sigouts[0].enables[1].value(0)
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
    sr860=False,
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
        if not TC:
            timeconst = station.__getattr__(mflis[0]).demods[0].timeconstant()
        else:
            pass
    elif sr860: # in that case, we lock on the first sr860
        sr860s = _list_sr860(station)
        if not TC:
            timeconst = station.__getattr__(sr860s[0].time_constant())
        else:
            pass
        station.__getattr__(sr830s[0]).reference_source('external')
    else:
        station.__getattr__(sr830s[0]).reference_source('internal')
        station.__getattr__(sr830s[0]).amplitude(ampl)
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
        
        
def init_sr860(
    station: Station,
    mfli=False,
    freq: Optional[float] = 127,
    ampl: Optional[float] = 1,
    TC: Optional[float] = None,
    filter: Optional[bool] = True,
    sensitivity: Optional[float] = 20e-6,
    phase: Optional[float] = 0,
):
    sr860s = _list_sr860(station)

    if TC:
        timeconst = TC
    else:
        timeconst = 100/freq/2/pi

    if mfli:  # in that case, we lock everything on the first mfli
        mflis = _list_mflis(station)
        if not TC:
            timeconst = station.__getattr__(mflis[0]).demods[0].timeconstant()
        else:
            pass
        station.__getattr__(sr860s[0]).reference_source('EXT')
    else:
        station.__getattr__(sr860s[0]).reference_source('INT')
        station.__getattr__(sr860s[0]).amplitude(ampl)
        station.__getattr__(sr860s[0]).frequency(freq)

    for sr860 in sr860s:
        station.__getattr__(sr860).time_constant(timeconst)
        station.__getattr__(sr860).harmonic(1)
        station.__getattr__(sr860).input_config('a-b')
        station.__getattr__(sr860).input_shield('float')
        station.__getattr__(sr860).input_coupling('ac')
        station.__getattr__(sr860).phase(phase)
        station.__getattr__(sr860).sensitivity(sensitivity)

        if filter:
            station.__getattr__(sr860).sync_filter('on')
            station.__getattr__(sr860).filter_slope(18)
        else:
            station.__getattr__(sr860).sync_filter('off')

    for sr860 in sr860s[1:]:
        station.__getattr__(sr860).reference_source('EXT')


def enable_DC(station: Station, demods=[2]):
    mflis = _list_mflis(station)
    if len(demods) != len(mflis) and demods==[2]:
        demods=[2]*len(mflis)
    elif len(demods) != len(mflis):
        return ValueError
    i = 0
    for mfli in mflis:
        station.__getattr__(mfli).oscs[1].freq(0)
        station.__getattr__(mfli).demods[demods[i]].adcselect(0)
        station.__getattr__(mfli).demods[demods[i]].oscselect(1)
        station.__getattr__(mfli).demods[demods[i]].harmonic(1)
        station.__getattr__(mfli).demods[demods[i]].phaseshift(0)
        station.__getattr__(mfli).demods[demods[i]].sinc(0)
        station.__getattr__(mfli).demods[demods[i]].timeconstant(.1)
        station.__getattr__(mfli).demods[demods[i]].order(3)
        station.__getattr__(mfli).sigins[0].ac(0)
        i+=1
    print(f'DC enabled for {mflis}')


def disable_DC(station: Station, demods=[2]):
    mflis = _list_mflis(station)
    if len(demods) != len(mflis) and demods==[2]:
        demods=[2]*len(mflis)
    elif len(demods) != len(mflis):
        return ValueError
    for mfli in mflis:
        station.__getattr__(mfli).sigins[0].ac(1)
        
    station.__getattr__(mflis[0]).sigouts[0].enables[0].value(1)
    for mfli in mflis[1:]:
        station.__getattr__(mfli).demods[0].adcselect(0)
        station.__getattr__(mfli).extrefs[0].enable(1)
        station.__getattr__(mfli).sigouts[0].on(0)
        station.__getattr__(mfli).triggers.out[0].source(0)
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
    sr860s = _list_sr860(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).demods[0].sinc(1)
        print(f'SINC filter enabled for {mflis}')
    elif sr860s:
        for sr860 in sr860s:
            station.__getattr__(sr860).sync_filter('ON')
        print(f'SINC filter enabled for {sr860}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).sync_filter('on')
        print(f'SINC filter enabled for {sr830}')


def disable_sinc(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    sr860s = _list_sr860(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).demods[0].sinc(0)
        print(f'SINC filter disabled for {mflis}')
    elif sr860s:
        for sr860 in sr860s:
            station.__getattr__(sr860).sync_filter('OFF')
        print(f'SINC filter disabled for {sr860}')
    elif sr830s:
        for sr830 in sr830s:
            station.__getattr__(sr830).sync_filter('off')
        print(f'SINC filter disabled for {sr830}')


def measure_single_ended(station: Station):
    mflis = _list_mflis(station)
    sr830s = _list_sr830(station)
    sr860s = _list_sr860(station)
    if mflis:
        for mfli in mflis:
            station.__getattr__(mfli).sigins[0].diff(0)
        print(f'measure single end A signal for {mflis}')
    elif sr860s:
        for sr860 in sr
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
            if itm.__class__ == MFLIWithComplexSample:
                mflis.append(name)
    return mflis


def _list_sr830(station: Station):
    sr830s = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == SR830.SR830:  # TODO: check if bug
                sr830s.append(name)
    return sr830s

def _list_sr860(station: Station):
    sr860s = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == SR860.SR86°:
                sr860s.append(name)
    return sr860s


def _is_DC(station: Station):
    mfli = _list_mflis(station)[0]
    return not station.__getattr__(mfli).sigins[0].ac()
    # TODO: check that this works in real life


class ComplexSampleParameter(Parameter):
    def __init__(
        self, *args: Any, dict_parameter: Optional[Parameter] = None, **kwargs: Any
    ):
        super().__init__(*args, **kwargs)
        if dict_parameter is None:
            raise TypeError("ComplexCampleParameter requires a dict_parameter")
        self._dict_parameter = dict_parameter

    def get_raw(self) -> ParamRawDataType:
        values_dict = self._dict_parameter.get()
        return complex(values_dict["x"], values_dict["y"])


class MFLIWithComplexSample(zhinst.qcodes.MFLI):
    """
    This wrapper adds back a "complex sample" parameter to the demodulators such that
    we can use them in the way that we have done with "sample" parameter
    in version 0.2 of ZHINST-qcodes
    written by jenshnielsen: https://github.com/zhinst/zhinst-qcodes/issues/41
    """

    def __init__(self, name: str, serial: str, **kwargs: Any):
        super().__init__(
            name=name, serial=serial, **kwargs
        )
        for demod in self.demods:
            demod.add_parameter(
                "complex_sample",
                label="Vrms",
                vals=ComplexNumbers(),
                parameter_class=ComplexSampleParameter,
                dict_parameter=demod.sample,
                snapshot_value=False,
            )
            
        #for auxout in self.auxouts:
        #    auxout.add_parameter(
        #        "max_rate",
        #        unit='V/s',
        #        label='maximum sweeping rate',
        #        initial_value=0,
        #        get_cmd=None,
        #        set_cmd=None,
        #    )