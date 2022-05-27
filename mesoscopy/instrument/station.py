"""
station initialisation
"""

from typing import Optional  # , List
from qcodes import Station, Parameter, Instrument


def init_station(
    *MFLI_num: str,
    SRS_addr: list[str] = None,
    K2600_addr: str = None,
    K2400_addr: str = None,
    triton_addr: str = None,
    IPS120_addr: str = None,
    ITC503_addr: str = None,
    MercITC_addr: str = None,
    SMB100A_addr: str = None,
    SIM900_addr: str = None,
    current_range: Optional[float] = 10e-9,
):
    """ functions to initialise the station for that measurement """

    station = Station()
    if K2600_addr is not None:
        from ..instrument.smu import Keithley2600
        keithley2600 = create_instrument(Keithley2600, "keithley2600",
                                         address=K2600_addr,
                                         force_new_instance=True)
        add_to_station(keithley2600, station)

    if K2400_addr is not None:
        from ..instrument.smu.Keithley_2400 import Keithley_2400
        keithley2400 = create_instrument(Keithley_2400, "keithley2400",
                                         address=K2400_addr,
                                         force_new_instance=True)
        add_to_station(keithley2400, station)

    if triton_addr is not None:
        from ..instrument.magnet import Triton
        triton = create_instrument(Triton, "triton", address=triton_addr,
                                   port=33576, force_new_instance=True)
        add_to_station(triton, station)

    if IPS120_addr is not None:
        from ..instrument.magnet import OxfordInstruments_IPS120
        ips120 = create_instrument(OxfordInstruments_IPS120, "IPS120",
                                   address=IPS120_addr,
                                   force_new_instance=True)
        add_to_station(ips120, station)

    if ITC503_addr is not None:
        from ..instrument.temperature import OxfordInstruments_ITC503
        itc503 = create_instrument(OxfordInstruments_ITC503, "ITC503",
                                   address=ITC503_addr,
                                   force_new_instance=True)
        add_to_station(itc503, station)

    if SMB100A_addr is not None:
        from ..instrument.rf import RohdeSchwarz_SMB100A
        smb100a = create_instrument(RohdeSchwarz_SMB100A, "SMB100A",
                                    address=SMB100A_addr,
                                    force_new_instance=True)
        add_to_station(smb100a, station)

    if SIM900_addr is not None:
        from ..instrument.smu import SRS_SIM928
        sim900 = create_instrument(SRS_SIM928, 'SIM900',
                                   address=SIM900_addr,
                                   force_new_instance=True)
        add_to_station(sim900, station)

    from zhinst.qcodes import MFLI

    for mf in list(MFLI_num):
        num = str(mf)
        locals()['mf' + num] = create_instrument(MFLI, 'mf' + num,
                                                 'dev' + num,
                                                 force_new_instance=True)
        add_to_station(locals()['mf' + num], station)

    from qcodes.instrument_drivers.stanford_research.SR830 import SR830
    n = 0
    for sr in list(SRS_addr):
        num = str(n)
        locals()['sr830_' + num] = create_instrument(SR830, 'sr830_' + num,
                                                     str(sr),
                                                     force_new_instance=True)
        add_to_station(locals()['sr830_' + num], station)
        n += 1

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
