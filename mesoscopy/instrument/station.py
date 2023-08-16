"""
station initialisation
"""

from typing import Optional, Tuple, Union  # , List
from qcodes import Station, Parameter, Instrument


def init_station(
    *MFLI_num: str,
    SR830_addr: list[str] = None,
    SR860_addr: list[str] = None,
    K2600_addr: str = None,
    K2400_addr: list[str] = None,
    triton_addr: str = None,
    IPS120_addr: str = None,
    ITC503_addr: str = None,
    MercITC_addr: str = None,
    Montana_addr: str = None,
    SMB100A_addr: str = None,
    SIM900_addr: str = None,
    CS580_addr: str = None,
    Thorlab_addr: list[Union[int, Tuple[int,str]]] = None,
    Thorlab_labels: Optional[list[str]] = None,
    arduino_2ch_addr: str = None,
    arduino_1ch_addr: str = None,
    current_range: Optional[float] = 10e-9,
):
    """
    Function to initialise a station
    
    Parameters
    ----------
    *MFLI_num: str
        serial number identifying Zurich Instruments’ MFLI lock-in amplifier
    SR830_addr: list[str]
        list of VISA addresses for the Stanford Research Systems’ SR830 lock-in amplifiers
    SR860_addr: list[str]
        list of VISA addresses for the Stanford Research Systems’ SR860 lock-in amplifiers
    K2600_addr: str
        VISA address for one Keithley 26 series source-measurement unit
    K2400_addr: list[str]
        list of VISA addresses for Keithley 24 series source-measurement units
    triton_addr: str
        IP address for an Oxford Instruments Triton dilution refrigerator
    IPS120_addr: str
        VISA address for one Oxford Instrument IPS120 magnet controller
    ITC503_addr: str
        VISA address for one Oxford Instrument ITC503 temperature controller
    MercITC_addr: str
        VISA address for one Oxford Instruments Mercury ITC temperature controller
    Montana_addr: str
        IP address for one Montana Instruments Cryostation
    SMB100A_addr: str
        VISA address for one Rohde&Schwarz SMB 100A RF source
    SIM900_addr: str
        VISA address for one Stanford Research Systems SIM900
    CS580_addr: str
        VISA address for one Stanford Research System CS580 current source
    Thorlab_addr: list[int] or list[Tuble[int, str]]
        list of VISA addresses for Thorlab drivers. Also accepts a tuple containing
        the address (int) and a label (str)
    arduino_2ch_addr: str
        Serial address for a 2-channel arduino controller
    arduino_1ch_addr: str
        Serial address for a 1-channel arduino controller
    current_range: float
        manual parameter.
    """

    station = Station()
    if K2600_addr is not None:
        from ..instrument.smu import Keithley2600
        keithley2600 = create_instrument(Keithley2600, "keithley2600",
                                         address=K2600_addr,
                                         force_new_instance=True)
        add_to_station(keithley2600, station)

    if K2400_addr is not None:
        from ..instrument.smu import Keithley2400
        n = 0
        for k24 in K2400_addr:
            num = str(n)
            locals()['keithley24_' + num] = create_instrument(Keithley2400,
                                         "keithley24_" + num,
                                         address=k24,
                                         force_new_instance=True)
            add_to_station(locals()['keithley24_' + num], station)
            n += 1

    if triton_addr is not None:
        from ..instrument.magnet import Triton
        triton = create_instrument(Triton, "triton", address=triton_addr,
                                   port=33576, force_new_instance=True)
        add_to_station(triton, station)

    if IPS120_addr is not None:
        from ..instrument.magnet import OxfordInstruments_IPS120
        ips120 = create_instrument(OxfordInstruments_IPS120, "IPS120",
                                   address=IPS120_addr, use_gpib=True,
                                   force_new_instance=True)
        add_to_station(ips120, station)

    if ITC503_addr is not None:
        from ..instrument.temperature import OxfordInstruments_ITC503
        itc503 = create_instrument(OxfordInstruments_ITC503, "ITC503",
                                   address=ITC503_addr,
                                   force_new_instance=True)
        add_to_station(itc503, station)

    if MercITC_addr is not None:
        from ..instrument.temperature import OxfordInstruments_MercuryITC
        mercITC = create_instrument(OxfordInstruments_MercuryITC, 'MercuryITC',
                                    address=MercITC_addr,
                                    force_new_instance=True)
        add_to_station(mercITC, station)
        
    if Montana_addr is not None:
        from ..instrument.temperature import MontanaInstruments_Cryostation
        mont_cryo = create_instrument(MontanaInstruments_Cryostation, 'Montana',
                                      address=Montana_addr, port=7773,
                                      force_new_instance=True)
        add_to_station(mont_cryo, station)

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

    if CS580_addr is not None:
        from ..instrument.source import CS580
        cs580 = create_instrument(CS580, 'cs580',
                                  address=CS580_addr,
                                  force_new_instance=True)
        add_to_station(cs580, station)
        
    if Thorlab_addr is not None:
        from ..instrument.motion_control import Thorlabs_general, _Thorlabs_APT
        n = 0
        for device in Thorlab_addr:
            if type(device) == int:
                dev_id = device
                dev_label = str(n)
            else:
                dev_id = device[0]
                dev_label = str(n) + '_' + device[1]
            instr = _Thorlabs_APT().get_hw_info(dev_id)[0]
            locals()[f'{instr}_{dev_label}'] = create_instrument(
                Thorlabs_general, f'{instr}_{dev_label}',
                device_id = dev_id,
                apt = _Thorlabs_APT(),
                force_new_instance=True)
            add_to_station(locals()[f'{instr}_{dev_label}'], station)
            n+=1
            
    if arduino_2ch_addr is not None:
        from ..instrument.motion_control import arduino2ch_stage
        arduino_2ch = create_instrument(arduino2ch_stage, 'arduinoXY',
                                        address=arduino_2ch_addr,
                                        force_new_instance=True)
        add_to_station(arduino_2ch, station)
        
    if arduino_1ch_addr is not None:
        from ..instrument.motion_control import arduino1ch_stage
        arduino_1ch = create_instrument(arduino1ch_stage, 'arduinoZ',
                                        address=arduino_1ch_addr,
                                        force_new_instance=True)
        add_to_station(arduino_1ch, station)

    from ..instrument.lockin import MFLIWithComplexSample

    for mf in list(MFLI_num):
        num = str(mf)
        locals()['mf' + num] = MFLIWithComplexSample(name='mf' + num,
                                    host='localhost',
                                    serial='dev' + num)
        add_to_station(locals()['mf' + num], station)

    if SR830_addr is not None:
        from qcodes.instrument_drivers.stanford_research.SR830 import SR830
        n = 0
        for sr in SR830_addr:
            num = str(n)
            locals()['sr830_' + num] = create_instrument(SR830, 'sr830_' + num,
                                                         str(sr),
                                                         force_new_instance=True)
            add_to_station(locals()['sr830_' + num], station)
            n += 1
            
    if SR860_addr is not None:
        from qcodes.instrument_drivers.stanford_research.SR860 import SR860
        n = 0
        for sr in SR860_addr:
            num = str(n)
            locals()['sr860_' + num] = create_instrument(SR860, 'sr860_' + num,
                                                         str(sr),
                                                         force_new_instance=True)
            add_to_station(locals()['sr860_' + num], station)
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
