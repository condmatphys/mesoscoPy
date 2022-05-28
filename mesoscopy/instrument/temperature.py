import logging
from qcodes import VisaInstrument
from qcodes.utils.validators import Ints, Enum, Numbers
from qcodes.utils.helpers import create_on_off_val_mapping
import pyvisa
from time import sleep


# -----------------------------
# temperature controler drivers
# -----------------------------

log = logging.getLogger(__name__)

class OxfordInstruments_ITC503(VisaInstrument):
    """
    This is the driver for the Oxford Insruments ITC 50 Temperature Controller

    The ITC503 can connect through both RS232 serial as well as GPIB.
    The commands sent in both cases are similar. When using the serial connection,
    commands are prefaced with '@n' where n is the ISOBUS number.
    """

    _GET_STATUS_MODE = {
        0: 'Local and locked',
        1: 'Remote and locked',
        2: 'Local and unlocked',
        3: 'Remote and unlocked'
    }

    _GET_AUTO_MAN_STATUS = {
        0: 'Heater manual and gas manual',
        1: 'Heater auto and gas manual',
        2: 'Heater manual and gas auto',
        3: 'Heater auto and gas auto'
    }

    _GET_SWEEP_STATUS = {
        0: 'Sweep not running',
        1: 'Sweeping to step 1',
        2: 'Holding sweep at step 1',
        3: 'Sweeping to step 2',
        4: 'Holding sweep at step 2',
        5: 'Sweeping to step 3',
        6: 'Holding sweep at step 3',
        7: 'Sweeping to step 4',
        8: 'Holding sweep at step 4',
        9: 'Sweeping to step 5',
        10: 'Holding sweep at step 5',
        11: 'Sweeping to step 6',
        12: 'Holding sweep at step 6',
        13: 'Sweeping to step 7',
        14: 'Holding sweep at step 7',
        15: 'Sweeping to step 8',
        16: 'Holding sweep at step 8',
        17: 'Sweeping to step 9',
        18: 'Holding sweep at step 9',
        19: 'Sweeping to step 10',
        20: 'Holding sweep at step 10',
        21: 'Sweeping to step 11',
        22: 'Holding sweep at step 11',
        23: 'Sweeping to step 12',
        24: 'Holding sweep at step 12',
        25: 'Sweeping to step 13',
        26: 'Holding sweep at step 13',
        27: 'Sweeping to step 14',
        28: 'Holding sweep at step 14',
        29: 'Sweeping to step 15',
        30: 'Holding sweep at step 15',
        31: 'Sweeping to step 16',
        32: 'Holding sweep at step 16'
    }

    _GET_HEATER_SENSOR = {
        1: 'Heater sensor 1',
        2: 'Heater sensor 2',
        3: 'Heater sensor 3'
    }


    _WRITE_WAIT = 100e-3  # sec.


    def __init__(self, name, address, use_gpib=True, number=2, **kwargs):
        """Initializes the Oxford Instruments ITC503 Temperature Controller

        Args:
            name (str)      : name of the instrument
            address (str)   : instrument _address
            use_gpib (bool) : whether to use GPIB or serial
            number (int)    : ISOBUS instrument number. ignored if using GPIB
        """
        super().__init__(name, address, terminator='\r',**kwargs)

        self._address = address
        self._number = number
        self._values = {}
        self._use_gpib = use_gpib

        # Add parameters
        self.add_parameter('mode',
                           get_cmd=self._get_mode,
                           set_cmd=self._set_mode,
                           vals=Ints())
        self.add_parameter('temperature',
                           unit='K',
                           get_cmd=self._get_temperature,
                           set_cmd=self._set_temperature)

        if not self._use_gpib:
            self.visa_handle.set_visa_attribute(
                visa.constants.VI_ATTR_ASRL_STOP_BITS,
                visa.constants.VI_ASRL_STOP_TWO)
            try:
                self.visa_handle.write('@%s%s' %(self._number, 'V'))
                sleep(self._WRITE_WAIT)
                self._read()
            except visa.VisaIOError:
                pass

    def get_all(self):
        """
        Reads all implemented parameters from insrtuments, update the wrapper
        """
        self.snapshot(update=True)

    def remote(self):
        """Set control to remote and unlocked"""
        self.log.info('Set control to remote and unlocked')
        self.remote_status(3)

    def local(self):
        """Set control to local and unlocked"""
        self.log.info('Set control to local and unlocked')
        self.remote_status(2)

    def close(self):
        """Safely close connection"""
        self.log.info('Closing ITC503 connection')
        self.local()
        super().close()

    def get_idn(self):
        """
        Overrides the function of Instrument since ITC503 does not support `*IDN?`
        Returns:
            dict containing vendor, model, serial, firmware
        """
        idparts = ['Oxford Instruments', 'ITC503', None, None]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'),idparts))

    def get_PID(self):
        P = self._get_P
        I = self._get_I
        D = self._get_D
        return P, I, D

    def identify(self):
        """Identify the device"""
        self.log.info('Identify the device')
        return self._execute('V')

    def _examine(self):
        """Examine the status of the device"""
        self.log.info('Examine status')
        result = self._execute('X')
        A = int(result[3])
        C = int(result[5])
        S = int(result[7:9])
        H = int(result[10])
        L = int(result[12])
        return A, C, S, H, L

    def examine(self):
        print('Activity: ')
        #_GET_AUTO_MAN_STATUS()

        print('Local/Remote status: ')
        #_GET_STATUS_MODE

        print('Sweep status: ')
        #_GET_SWEEP_STATUS

        print('Control sensor: ')
        #_GET_HEATER_SENSOR

        print('Mode: ')
        #0: disapble auuto-pid
        # 1: use auto-pid


    # TODO: 'V' gives version in the form:
    # 'ITC503 Version 1.1 (c) OXFORD 1997'
    # 'Pnnnn' sets P of PID, same for 'Innnn' and 'Dnnnn'


    def _execute(self, message):
        """ write a command to the device, return the result
        Args:
            message (str): command for the device
        """
        self.log.info('Send the following command to ITC503: %s' %message)
        if self._use_gpib:
            return self.ask(message)

        self.visa_handle.write('@%s%s' %(self._number, message))
        sleep(self._WRITE_WAIT)
        result = self._read()
        if result.find('?') >= 0:
            print('Error: Command %s not recognised' %message)
        else:
            return result

    def _get_set_temperature(self):
        self.log.info('Read ITC503 Set Temperature')
        result = self._execute('R0')
        return float(result[1:])

    def _get_sensor1_temperature(self):
        self.log.info('Read ITC503 Sensor 1 Temperature')
        result = self._execute('R1')
        return float(result[1:])

    def _get_sensor2_temperature(self):
        self.log.info('Read ITC503 Sensor 2 Temperature')
        result = self._execute('R2')
        return float(result[1:])

    def _get_sensor3_temperature(self):
        self.log.info('Read ITC503 Sensor 3 Temperature')
        result = self._execute('R3')
        return float(result[1:])

    def _get_temperature_error(self):
        self.log.info('Read ITC503 Temperature Error (+ve when SET>Measured)')
        result = self._execute('R4')
        return float(result[1:])

    def _get_heater_percent(self):
        self.log.info('Read ITC503 Heater O/P (%)')
        result = self._execute('R5')
        return float(result[1:])

    def _get_heater_volt(self):
        self.log.info('Read ITC503 Heater O/P (Volts)')
        result = self._execute('R6')
        return float(result[1:])

    def _get_gasflow(self):
        self.log.info('Read ITC503 Gas Flow O/P (arb. units.)')
        result = self._execute('R7')
        return float(result[1:])

    def _get_P(self):
        self.log.info('Read ITC503 Proportional band')
        result = self._execute('R8')
        return float(result[1:])

    def _get_I(self):
        self.log.info('Read ITC503 Integral Action Time')
        result = self._execute('R9')
        return float(result[1:])

    def _get_D(self):
        self.log.info('Read ITC503 Derivative Action Time')
        result = self._execute('R10')
        return float(result[1:])

    def _get_mode(self):
        """get the mode of the device.
        Returns:
            mode(str): see _GET_STATUS_MODE.
        """
        self.log.info('Get ITC503 mode')
        result = self._execute('X')
        return self._GET_STATUS_MODE[int(result[6])]

    def _set_mode(self, mode):
        """
        Args:
            mode(int): see dictionary of allowed values _GET_STATUS_MODE
        """
        if mode in self._GET_STATUS_MODE.keys():
            self.log.info('Setting device mode to %s' %self._GET_STATUS_MODE[mode])
            self.remote()
            self._execute('M%s' %mode)
            self.local()
        else:
            print('Invalid mode inserted.')
