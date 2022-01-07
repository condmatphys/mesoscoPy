"""
station initialisation
"""

from typing import Optional, List
from qcodes import Station, Parameter, Instrument


def init_station(
    *MFLI_num: str,
    SRS_addr: List(str) = None,
    SMU_addr: str = None,
    triton_addr: str = None,
    rf_addr: str = None,
    SIM_addr: str = None,
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

    if SIM_addr is not None:
        from ..instrument.smu import SRS_SIM928
        sim = create_instrument(SRS_SIM928, 'SIM900',
                                address=SIM_addr,
                                force_new_instance=True)
        add_to_station(sim, station)

    from zhinst.qcodes import MFLI

    for mf in list(MFLI_num):
        num = str(mf)
        locals()['mf' + num] = create_instrument(MFLI, 'mf' + num,
                                                 'dev' + num,
                                                 force_new_instance=True)
        add_to_station(locals()['mf' + num], station)

    from qcodes.instrument_drivers.stanford_research.SR830 import SR830
    num = 0
    for sr in list(SRS_addr):
        locals()['sr830_' + num] = create_instrument(SR830, 'sr830_' + num,
                                                     str(sr),
                                                     force_new_instance=True)
        add_to_station(locals()['sr830_' + num], station)
        num += 1

    curr_range = Parameter('current_range', label='current range',
                           unit='A/V', set_cmd=None, get_cmd=None)
    curr_range.set(current_range)
    add_to_station(curr_range, station)

    return station


def close_station(station):
    """
    TODO: need to create this function.
    goal:
        a) sweep everything to 0
        b) disconnect_instrument(name)
        """


def create_instrument(self, name, *arg, **kwarg):
    """
    create a new instrument, of type <self> and name <name>.
    optional kwargs:
        force_new: False
            when True, it first closes the instrument and recreate
    """

    force_new = kwarg.pop('force_new_instance', False)

    try:
        return self(name, *arg, **kwarg)
    except KeyError:
        print(f"Instrument {name} exists.")
        if force_new:
            print(f"closing and recreating instrument {name}.")
            Instrument._all_instruments[name]().close()
            return self(name, *arg, **kwarg)

        return Instrument._all_instruments[name]()


def disconnect_instrument(name):
    """
    force disconnect an instrument
    """
    Instrument._all_instruments[name]().close()


def add_to_station(instrument, station):
    """
    add instrument <instrument> to station <station>.
    """

    if instrument.name in station.components:
        del station.components[instrument.name]

    station.add_component(instrument)
    return station
