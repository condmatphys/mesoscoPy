import logging
from qcodes import VisaInstrument
from qcodes.utils.validators import Ints, Enum, Numbers, Sequence
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

    With the following driver, ITC503 should connect through GPIB.
    """

    _GET_STATUS_REMOTE = {
        0: 'Local and locked',
        1: 'Remote and locked',
        2: 'Local and unlocked',
        3: 'Remote and unlocked'
    }

    _GET_ACTIVITY_STATUS = {
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

    _GET_PID_MODE = {
        0: 'Auto-PID disabled',
        1: 'Auto-PID enabled'
    }


    _WRITE_WAIT = 100e-3  # sec.


    def __init__(self, name, address, number=2, **kwargs):
        """Initializes the Oxford Instruments ITC503 Temperature Controller

        Args:
            name (str)      : name of the instrument
            address (str)   : instrument _address
            number (int)    : ISOBUS instrument number. ignored if using GPIB
        """
        super().__init__(name, address, terminator='\r',**kwargs)

        self._address = address
        self._number = number
        self._values = {}

        # Add parameters
        self.add_parameter('T1',
                           unit='K',
                           get_cmd=self._get_T1,
                           vals=Numbers(0,1000))
        self.add_parameter('T2',
                           unit='K',
                           get_cmd=self._get_T2,
                           vals=Numbers(0,1000))
        self.add_parameter('T3',
                           unit='K',
                           get_cmd=self._get_T3,
                           vals=Numbers(0,1000))
        self.add_parameter('activity_status',
                           get_cmd=self._get_activity_status,
                           set_cmd=self._set_activity_status,
                           vals=Ints(0,3))
        self.add_parameter('remote_status',
                           get_cmd=self._get_remote_status,
                           set_cmd=self._set_remote_status,
                           vals=Ints())
        self.add_parameter('PID',
                           get_cmd=self.get_PID,
                           set_cmd=self.set_PID,
                           vals=Sequence(length=3))
        self.add_parameter(name='pid_control_channel',
                           label='PID control channel',
                           get_cmd=self._get_pid_control_channel,
                           set_cmd=self._set_pid_control_channel,
                           vals=Ints(1, 3))
        self.add_parameter(name='pid_mode',
                           label='PID Mode',
                           get_cmd=self._get_pid_mode,
                           set_cmd=self._set_pid_mode)
        self.add_parameter(name='pid_ramp',
                           label='PID ramp',
                           get_cmd=self._get_pid_ramp,
                           set_cmd=self._set_pid_ramp)
        self.add_parameter(name='pid_setpoint',
                           label='PID temperature setpoint',
                           unit='K',
                           get_cmd=self._get_pid_setpoint,
                           set_cmd=self._set_pid_setpoint)
        self.add_parameter(name='gas_flow',
                           label='Gas Flow',
                           unit='%',
                           get_cmd=self._get_gasflow,
                           set_cmd=self._set_gasflow,
                           vals=Numbers(0,99.9))
        
    def get_all(self):
        """
        Reads all implemented parameters from instruments, update the wrapper
        """
        self.snapshot(update=True)
        
    def _get_activity_status(self):
        """get activity status. returns one of the values in _GET_ACTIVITY_STATUS"""
        self.log.info('Get activity status')
        result = self._execute('X')
        return self._GET_ACTIVITY_STATUS[int(result[3])]
    
    def _set_activity_status(self, mode):
        """
        Args:
            mode(int): see dictionary of allowed values _GET_ACTIVITY_STATUS
        """
        if mode in self._GET_ACTIVITY_STATUS.keys():
            self.log.info(f'Setting device activity status to {self._GET_ACTIVITY_STATUS[mode]}')
            self._execute(f'A{mode}')
        else:
            print('Invalid mode inserted')
        
    def _get_remote_status(self):
        """get remote control status. returns one of the values in _GET_STATUS_REMOTE."""
        self.log.info('Get remote control status')
        result = self._execute('X')
        return self._GET_STATUS_REMOTE[int(result[5])]

    def _set_remote_status(self, mode):
        """
        Args:
            mode(int): see dictionary of allowed values _GET_STATUS_REMOTE
        """
        if mode in self._GET_STATUS_REMOTE.keys():
            self.log.info(f'Setting device remote status to {self._GET_STATUS_REMOTE[mode]}')
            self._execute(f'C{mode}')
        else:
            print('Invalid mode inserted.')
            
    def _get_pid_mode(self):
        self.log.info('Get PID mode status')
        result = self._execute('X')
        return self._GET_PID_MODE[int(result[12])]
        
    def _set_pid_mode(self, mode):
        """Set PID to Auto/Manual"""
        if mode in self._GET_STATUS_REMOTE.keys():
            self.log.info(f'Set PID Control to {self._GET_PID_MODE[mode]}')
            self._execute(f'L{mode}')
        else:
            print('Invalid mode inserted.')
            
    def _get_pid_ramp(self):
        """get Ramp status"""
        self.log.info('Get PID ramp status')
        result = self._execute('X')
        return self._GET_SWEEP_STATUS[int(result[7:9])]
        
    def _set_pid_ramp(self, mode):
        """Start / stop a ramp"""
        if mode in self._GET_SWEEP_STATUS.keys():
            self.log.info(f'Set PID ramp to {mode}')
            self._execute(f'S{mode}')
        else:
            print('Invalid mode inserted')

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
        P = self._get_P()
        I = self._get_I()
        D = self._get_D()
        return P, I, D
    
    def set_PID(self, seq):
        P, I, D = seq
        self._execute('P%s'%round(P,4))
        sleep(self._WRITE_WAIT)
        self._execute('I%s'%round(I,4))
        sleep(self._WRITE_WAIT)
        self._execute('D%s'%round(D,4))
        sleep(self._WRITE_WAIT)

    def identify(self):
        """Identify the device"""
        self.log.info('Identify the device')
        return self._execute('V')

    def examine(self):
        print('Activity: ')
        self.activity_status()

        print('Local/Remote status: ')
        self.remote_status()

        print('Sweep status: ')
        self.pid_ramp()

        print('Control sensor: ')
        self.pid_control_channel()

        print('PID Mode: ')
        self.pid_mode()

    def _execute(self, message):
        """ write a command to the device, return the result
        Args:
            message (str): command for the device
        """
        self.log.info('Send the following command to ITC503: %s' %message)
        return self.ask(message)
    
    def _get_pid_control_channel(self):
        self.log.info('Get heater control channel')
        result = self._execute('X')
        return result[10]
    
    def _set_pid_control_channel(self, number):
        """select heater number"""
        self.log.info(f'Set ITC503 heater to {number}')
        self.remote()
        self._execute(f'H{number}')
        self.local()

    def _get_pid_setpoint(self):
        self.log.info('Read ITC503 Set Temperature')
        result = self._execute('R0')
        return float(result.replace('R', ''))
    
    def _set_pid_setpoint(self, temp):
        self.log.info(f'Setting target temperature to {temp}')
        self.remote()
        self._execute(f'T{round(temp,4)}')
        self.local()

    def _get_T1(self):
        self.log.info('Read ITC503 Sensor 1 Temperature')
        result = self._execute('R1')
        return float(result.replace('R', ''))

    def _get_T2(self):
        self.log.info('Read ITC503 Sensor 2 Temperature')
        result = self._execute('R2')
        return float(result.replace('R', ''))

    def _get_T3(self):
        self.log.info('Read ITC503 Sensor 3 Temperature')
        result = self._execute('R3')
        return float(result.replace('R', ''))

    def get_temperature_error(self):
        self.log.info('Read ITC503 Temperature Error (+ve when SET>Measured)')
        result = self._execute('R4')
        return float(result.replace('R', ''))

    def get_heater_percent(self):
        self.log.info('Read ITC503 Heater O/P (%)')
        result = self._execute('R5')
        return float(result.replace('R', ''))

    def get_heater_volt(self):
        self.log.info('Read ITC503 Heater O/P (Volts)')
        result = self._execute('R6')
        return float(result.replace('R', ''))

    def _get_gasflow(self):
        self.log.info('Read ITC503 Gas Flow O/P (%)')
        result = self._execute('R7')
        return float(result.replace('R', ''))/10
    
    def _set_gasflow(self, number):
        self.log.info(f'Set ITC503 Gas flow to {number}%')
        num = int(number*10)
        self._execute(f'G{num}')

    def _get_P(self):
        self.log.info('Read ITC503 Proportional band')
        result = self._execute('R8')
        return float(result.replace('R', ''))

    def _get_I(self):
        self.log.info('Read ITC503 Integral Action Time')
        result = self._execute('R9')
        return float(result.replace('R', ''))

    def _get_D(self):
        self.log.info('Read ITC503 Derivative Action Time')
        result = self._execute('R10')
        return float(result.replace('R', ''))


    # LIST OF COMMANDS

    #
    # Control:
    # Mnnn: set maximum heater volts limit
    # Onnn: set output volts
