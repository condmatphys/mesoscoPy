"""
station initialisation
"""

from typing import Optional
from qcodes import Station, Parameter
from ..instrument.instrument_tools import create_instrument, add_to_station


def init_station(
    *MFLI_num: str,
    SMU_addr: str = None,
    triton_addr: str = None,
    rf_addr: str = None,
    current_range: Optional[float] = 10e-9,
):
    """ functions to initialise the station for that measurement """
    # TODO: make this useable with different keithley types, SR830 lock-ins and
    # Oxford iPS/iTC magnet/PID controler. all arguments in the function should
    # be optional.

    station = Station()
    if SMU_addr is not None:
        from ..instrument.smu import Keithley2600
        keithley = create_instrument(Keithley2600, "keithley",
                                     address=SMU_addr,
                                     force_new_instance=True)
        add_to_station(keithley, station)

    if triton_addr is not None:
        from ..instrument.magnet import Triton
        triton = create_instrument(Triton, "triton", address=triton_addr,
                                   port=33576, force_new_instance=True)
        add_to_station(triton, station)

    if rf_addr is not None:
        from ..instrument.rf import RohdeSchwarz_SMB100A
        rfsource = create_instrument(RohdeSchwarz_SMB100A, "rf_source",
                                     address=rf_addr,
                                     force_new_instance=True)
        add_to_station(rfsource, station)

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


def close_station(station):
    """ need to create this function.
    goal:
        a) sweep everything to 0
        b) disconnect_instrument(name)
        """
