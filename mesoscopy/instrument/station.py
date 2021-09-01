"""
station initialisation
"""

from typing import Optional
from qcodes import Station, Parameter
from ..instrument.instrument_tools import create_instrument, add_to_station


def init_station(
    keithley_addr: str,
    triton_addr: str,
    *MFLI_num: str,
    current_range: Optional[float] = 10e-9,
):
    """ functions to initialise the station for that measurement """
    # TODO: make this useable with different keithley types, SR830 lock-ins and
    # Oxford iPS/iTC magnet/PID controler. all arguments in the function should
    # be optional.

    station = Station()
    from ..instrument.keithley import Keithley2600
    keithley = create_instrument(Keithley2600, "keithley",
                                 address=keithley_addr,
                                 force_new_instance=True)
    add_to_station(keithley, station)

    from qcodes.instrument_drivers.oxford.triton import Triton
    triton = create_instrument(Triton, "triton", address=triton_addr,
                               port=33576, force_new_instance=True)
    add_to_station(triton, station)

    from zhinst.qcodes import MFLI

    for mf in list(MFLI_num):
        num = str(mf)
        locals()['mf' + num] = create_instrument(MFLI, 'mf' + num,
                                                 'dev' + num,
                                                 force_new_instance=True)
        add_to_station(locals()['mf' + num], station)

    curr_range = Parameter('current_range', label='current range',
                           unit='A/V', set_cmd=None, get_cmd=None)
    curr_range.set(current_range)
    add_to_station(curr_range, station)

    return station
