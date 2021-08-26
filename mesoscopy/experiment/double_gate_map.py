"""
functions to make a double gate map
works with Keithley 2600, Oxford Triton and Zurich Instrument lock-in amplifiers
"""


import time
from qcodes import Station, Instrument, Parameter
from qcodes.instrument.channel import InstrumentChannel
from qcodes.instrument.parameter import _BaseParameter

from ..instrument.instrument_tools import create_instrument, add_to_station

def station_triton(
    keithley_addr: str,
    triton_addr: str,
    *MFLI_num: str,
    current_range: Optional[float] = 10e-9
    ):
    """ functions to initialise the station for that measurement """

    station = Station()
    from qcodes.instrument_drivers.tektronix.Keithley_2600_channels import \
        Keithley_2600
    keithley = create_instrument(Keithley_2600, "keithley",
                                 address=keithley_addr,
                                 force_new_instance=True)
    add_to_station(keithley, station)

    from qcodes.instrument_drivers.oxford.triton import Triton
    triton = create_instrument(Triton, "triton", address=triton_addr,
                               port=33576, force_new_instance=True)
    add_to_station(triton, station)

    from zhinst.qcodes import MFLI

    for mf in list(MFLI_num):
        locals()['mf' + MFLI_num] = create_instrument(MFLI, 'mf' + MFLI_num,
                                                      'dev' + MFLI_num,
                                                      force_new_instance=True)
        add_to_station(locals()['mf' + MFLI_num], station)

    curr_range = Parameter('current_range', label='current range',
    unit='A/V', set_cmd=None, get_cmd=None)
    curr_range.set(current_range)
    add_to_station(curr_range)

    return station

def _go_to(v0, v1,
           channel: InstrumentChannel,
           desc: Optional[str] = None,
           threshold: Optional[float] = None,
):
    array = generate_1D_sweep_array(v0, v1, step=2e-1)
    time.sleep(.5)
    for v in tqdm(array, leave=False, desc=desc):
        channel.volt(v)
        time.sleep(0.1)
        if threshold and channel.curr() > threshold:
            break
    time.sleep(.5)
    return v


def gate_map(
    xarray,
    inner_delay,
    yarray, outer_delay,
    station: Station,
    exp: Optional[Experiment] = None,
    label: Optional[str] = None
):

    station.keithley.smua.mode('voltage')
    station.keithley.smua.nplc(0.05)
    station.keithley.smua.sourcerange_v(20)
    station.keithley.smua.limitv(20)
    station.keithley.smua.measurerange_i(1e-7)
    station.keithley.smua.limiti(1e-9)
    station.keithley.smua.output('on')

    station.keithley.smub.mode('voltage')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_v(200)
    station.keithley.smub.limitv(70)
    station.keithley.smub.measurerange_i(1e-7)
    station.keithley.smub.limiti(1e-9)
    station.keithley.smub.output('on')

    lockins = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                lockins.append(name)
    init_tg = station.keithley.smua.volt()
    init_bg = station.keithley.smub.volt()

    _go_to(init_tg, xarray[0], station,
           desc=f'sweeping top gate to {init_tg} V')

    _go_to(init_bg, yarray[0], station,
           desc=f'sweeping back gate to {init_bg} V')

    raw_data = sweep2d(
        param_setx=station.keithley.smua.volt,
        xarray=xarray,
        inner_delay=inner_delayfloat,
        param_sety=station.keithley.smub.volt,
        yarray=yarray,
        outer_delay=outer_delay,
        *[station.__getattr__(lockin).demods[0].sample() for lockin in lockins],
        station.triton.T5,
        exp=exp,
        measurement_name=f'gate map {label}',
        use_threads: Optional[bool] = True,
        measure_retrace: Optional[bool] = True,
        num_retrace: Optional[str] = 401
        )

    return raw_data