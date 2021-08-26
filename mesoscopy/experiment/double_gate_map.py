"""
functions to make a double gate map
works with Keithley 2600, Oxford Triton and Zurich Instrument lock-in amplifiers
"""


import time
from qcodes import Station

from ..instrument.instrument_tools import create_instrument, add_to_station

def station_triton(
    keithley_addr: str,
    triton_addr: str,
    *MFLI_num: str
    ):
    """ functions to initialise the station for that measurement """

    station = Station()
    from qcodes.instrument_drivers.tektronix.Keithley_2600_channels import \
        Keithley_2600
    keithley = create_instrument(Keithley_2600, "keithley",
                                 address=keithley_addr,
                                 force_new_instance=True)
    add_to_station(keithley,station)

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

    return station
