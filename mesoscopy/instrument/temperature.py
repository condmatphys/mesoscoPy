import logging
from qcodes import IPInstrument, VisaInstrument, Parameter
from qcodes.utils.validators import Ints, Enum, Numbers, Sequence
import qcodes.utils.validators as vals
from qcodes.utils.helpers import create_on_off_val_mapping
import pyvisa
from time import sleep
import time
from functools import partial

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

    _GET_OUTPUT_MODE = {
        0: 'Manual',
        1: 'Auto'
    }

    _WRITE_WAIT = 100e-3  # sec.


    def __init__(self, name, address, use_gpib=True, number=2, **kwargs):
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
        self._use_gpib = use_gpib

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
        self.add_parameter('gas_mode',
                           label='gas mode',
                           set_cmd=self._set_gas_mode,
                           get_cmd=self._get_gas_mode,
                           vals=vals.Numbers(0, 1))
        self.add_parameter('heater_sensor',
                           label='Heater sensor',
                           docstring='Specifies the sensor to be used for automatic PID control.',
                           set_cmd=self._set_heater_sensor,
                           get_cmd=self._get_heater_sensor,
                           vals=vals.Numbers(1, 3))
        self.add_parameter('heater_mode',
                           label='heater mode',
                           set_cmd=self._set_output_mode,
                           get_cmd=self._get_output_mode,
                           vals=vals.Numbers(0, 1))
        self.add_parameter('sweep',
                           label='Sweep',
                           set_cmd=self._set_sweep,
                           get_cmd=self._get_sweep_status,
                           vals=vals.Numbers(0, 1))

        if not self._use_gpib:
            self.visa_handle.set_visa_attribute(
                pyvisa.constants.VI_ATTR_ASRL_STOP_BITS,
                pyvisa.constants.VI_ASRL_STOP_TWO)
            # to handle VisaIOError at first read
            try:
                self.visa_handle.write(f'@{self._number} V')
                sleep(self._WRITE_WAIT)
                self._read()
            except pyvisa.VisaIOError:
                pass
        
    def get_all(self):
        """
        Reads all implemented parameters from instruments, update the wrapper
        """
        self.snapshot(update=True)
        
    def _get_activity_status(self):
        """get activity status. returns one of the values in _GET_ACTIVITY_STATUS"""
        self.log.info('Get activity status')
        result = self._execute('X\r')
        return self._GET_ACTIVITY_STATUS[int(result[3])]
    
    def _set_activity_status(self, mode):
        """
        Args:
            mode(int): see dictionary of allowed values _GET_ACTIVITY_STATUS
        """
        if mode in self._GET_ACTIVITY_STATUS.keys():
            self.log.info(f'Setting device activity status to {self._GET_ACTIVITY_STATUS[mode]}')
            self._execute(f'A{mode}\r')
        else:
            print('Invalid mode inserted')
        
    def _get_remote_status(self):
        """get remote control status. returns one of the values in _GET_STATUS_REMOTE."""
        self.log.info('Get remote control status')
        result = self._execute('X\r')
        return self._GET_STATUS_REMOTE[int(result[5])]

    def _set_remote_status(self, mode):
        """
        Args:
            mode(int): see dictionary of allowed values _GET_STATUS_REMOTE
        """
        if mode in self._GET_STATUS_REMOTE.keys():
            self.log.info(f'Setting device remote status to {self._GET_STATUS_REMOTE[mode]}')
            self._execute(f'C{mode}\r')
        else:
            print('Invalid mode inserted.')
            
    def _get_pid_mode(self):
        self.log.info('Get PID mode status')
        result = self._execute('X\r')
        return self._GET_PID_MODE[int(result[12])]
        
    def _set_pid_mode(self, mode):
        """Set PID to Auto/Manual"""
        if mode in self._GET_STATUS_REMOTE.keys():
            self.log.info(f'Set PID Control to {self._GET_PID_MODE[mode]}')
            self._execute(f'L{mode}\r')
        else:
            print('Invalid mode inserted.')
            
    def _get_pid_ramp(self):
        """get Ramp status"""
        self.log.info('Get PID ramp status')
        result = self._execute('X\r')
        return self._GET_SWEEP_STATUS[int(result[7:9])]
        
    def _set_pid_ramp(self, mode):
        """Start / stop a ramp"""
        if mode in self._GET_SWEEP_STATUS.keys():
            self.log.info(f'Set PID ramp to {mode}')
            self._execute(f'S{mode}\r')
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

        if self._use_gpib:
            self._clear()
            sleep(self._WRITE_WAIT)
            self.write(message)
            sleep(self._WRITE_WAIT)
            return self._read()

        self.visa_handle.write(f'@{self._number}{message}')
        sleep(self._WRITE_WAIT)
        result = self._read()
        if result.find('?') >=0:
            print(f'Error: command {message} not recognised')
        else:
            return result

    def _clear(self):
        self.visa_handle.clear()
        #print(f'buffer cleared on {self.name}')
    
    def _read(self):
        """reads the total bytes in the buffer and outputs as a string
        returns: message (str)"""
        return self.visa_handle.read(termination='\r')
    
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
        return float(result.replace('R', ''))
    
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

    def _set_gas_mode(self, n):
        output = int(self._execute(f'X')[3]) % 2
        return self._execute(f'A{output+2*int(n)}')

    def _get_gas_mode(self):
        result = self._execute(f'X')
        return self._GET_OUTPUT_MODE[int(int(result[3])/2)]

    def _set_output_mode(self, n):
        gas = int(int(self._execute(f'X')[3])/2)
        return self._execute(f'A{int(n)+gas*2}')

    def _get_output_mode(self):
        result = self._execute(f'X')
        return self._GET_OUTPUT_MODE[int(result[3]) % 2]

    def _set_heater_sensor(self, n):
        return self._execute(f'H{int(n)}')

    def _get_heater_sensor(self):
        result = self._execute(f'X')
        return int(result[10])

    def _set_sweep(self, n):
        return self._execute(f'S{n}')

    def _get_sweep_status(self):
        result = self._execute(f'X')
        return self._sweep_status(int(result[7:9]))

    def _sweep_status(self, n):
        if n == 0:
            return 'Sweep not running'
        elif n % 2 == 1:
            return f'Sweeping to step {(int(n)+1)/2}'
        else:
            return f'Holding at step {int(n)/2}'

    # LIST OF COMMANDS

    #
    # Control:
    # Mnnn: set maximum heater volts limit
    # Onnn: set output volts


class OxfordInstruments_MercuryITC(VisaInstrument):
    """
    Class to represent an Oxford Instruments MercuryiTC temperature controller
    """
    def __init__(self, name: str, address: str, **kwargs) -> None:
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA resource address
        """
        super().__init__(name, address, terminator='\r\n', **kwargs)

        self.sorb_temp = Parameter(
            "sorb_temp",
            unit="K",
            get_cmd="READ:DEV:MB1.T1:TEMP:SIG:TEMP",
            get_parser=self.__temp_from_string,
            instrument=self
        )

        self.he4_temp = Parameter(
            "he4_temp",
            unit="K",
            get_cmd="READ:DEV:DB6.T1:TEMP:SIG:TEMP",
            get_parser=self.__temp_from_string,
            instrument=self
        )

        self.he3_temp_high = Parameter(
            "he3_temp_high",
            unit="K",
            get_cmd="READ:DEV:DB7.T1:TEMP:SIG:TEMP",
            get_parser=self.__temp_from_string,
            instrument=self
        )

        self.he3_temp_low = Parameter(
            "he3_temp_low",
            unit="K",
            get_cmd="READ:DEV:DB8.T1:TEMP:SIG:TEMP",
            get_parser=self.__temp_from_string,
            instrument=self
        )

        self.low_temp_sensor_threshold = Parameter(
            "low_temp_sensor_threshold",
            unit="K",
            get_cmd="READ:DEV:HelioxX:HEL:LOWT",
            get_parser=self.__temp_from_string,
            instrument=self
        )

        self.he3_temp = Parameter(
            "he3_temp",
            unit="K",
            get_cmd = lambda: self.__valid_he3_temperature(),
            set_cmd = lambda T: self.__set_and_equilibrate_temp(T),
            instrument=self
        )

        self.temp_setpoint = Parameter(
            "temp_setpoint",
            unit="K",
            get_cmd = "READ:DEV:HelioxX:HEL:SIG:TSET",
            get_parser=self.__temp_from_string,
            set_cmd = lambda T: self.ask("SET:DEV:HelioxX:HEL:SIG:TSET:{:f}".format(T)), # Use ask to ignore return value
            vals=vals.Numbers(min_value=0, max_value=100), # Will not set above 100K, may want to change this later
            instrument=self
        )

        self.valve_setpoint = Parameter(
            "valve_setpoint",
            unit=r"%",
            get_cmd="READ:DEV:DB3.P1:PRES:LOOP:FSET",
            get_parser=self.__value_from_string,
            set_cmd = lambda F: self.ask("SET:DEV:DB3.P1:PRES:LOOP:FSET:{:f}".format(F)),  # Use ask to ignore return value
            vals = vals.Numbers(min_value=0, max_value=100),
            instrument=self
        )

        self.valve_position = Parameter(
            "valve_position",
            unit=r"%",
            get_cmd = "READ:DEV:DB4.G1:AUX:SIG:PERC",
            get_parser=self.__temp_from_string,
            set_cmd=self.valve_setpoint,
            vals = vals.Numbers(min_value=0, max_value=100),
            instrument=self
        )

        self.automatic_flow = Parameter(
            "automatic_flow",
            get_cmd = "READ:DEV:DB3.P1:PRES:LOOP:FAUT",
            set_cmd = lambda s: self.ask("SET:DEV:DB3.P1:PRES:LOOP:FAUT:{:s}".format(s)),
            get_parser=self.__value_from_string,
            val_mapping={True: "ON", False: "OFF"},
            instrument=self
        )

        self.pressure_setpoint = Parameter(
            "pressure_setpoint",
            unit="mbar",
            get_cmd = "READ:DEV:DB3.P1:PRES:LOOP:PRST",
            get_parser=self.__pres_from_string,
            set_cmd = lambda p: self.ask("SET:DEV:DB3.P1:PRES:LOOP:PRST:{:f}".format(p)),
            vals=vals.Numbers(min_value=0, max_value=1e3),
            instrument=self
        )

        self.pressure = Parameter(
            "pressure",
            unit="mbar",
            get_cmd="READ:DEV:DB3.P1:PRES:SIG:PRES",
            get_parser=self.__pres_from_string,
            set_cmd=self.__set_auto_pressure_value,
            vals=vals.Numbers(min_value=0, max_value=1e3),
            instrument=self
        )

        self.mode = Parameter(
            "mode",
            get_cmd="READ:DEV:HelioxX:HEL:SIG:STAT",
            get_parser=self.__value_from_string,
            instrument=self
        )

        self.equilibrium_time = Parameter(
            "equilibrium_time",
            unit="s",
            get_cmd=None,
            set_cmd=None,
            vals=vals.Numbers(min_value=0),
            initial_value=0,
            instrument=self
        )

        self.settle_time = Parameter(
            "settle_time",
            unit="s",
            get_cmd=None,
            set_cmd=None,
            vals=vals.Numbers(min_value=0),
            initial_value=0,
            instrument=self
        )

        self.equilibrium_tolerance = Parameter(
            "equilibrium_tolerance",
            unit="K",
            get_cmd=None,
            set_cmd=None,
            vals=vals.Numbers(min_value=0),
            initial_value=0.01,
            instrument=self
        )

        self.equilibrium_refresh_time = Parameter(
            "equilibrium_refresh_time",
            unit="s",
            get_cmd=None,
            set_cmd=None,
            vals=vals.Numbers(min_value=0),
            initial_value=1,
            instrument=self
        )

        self.connect_message()

    def difference_from_setpoint(self):
        return self.he3_temp() - self.temp_setpoint()

    def __temp_from_string(self, string):
        return float(string.split(":")[-1][:-2])

    def __pres_from_string(self, string):
        return float(string.split(":")[-1][:-3])

    def __value_from_string(self, string):
        return string.split(":")[-1][:-1]

    def __valid_he3_temperature(self):
        high_temp = self.he3_temp_high()
        low_temp = self.he3_temp_low()
        if high_temp > self.low_temp_sensor_threshold():
            return high_temp
        return low_temp

    def __stabilise_temperature(self):
        start_time = time.time()
        while time.time() - start_time < self.equilibrium_time(): # wait until at least the set equilibrium time has elapsed
            if abs(self.difference_from_setpoint()) > self.equilibrium_tolerance():
                start_time = time.time() # reset timer if not within tolerance
            sleep(self.equilibrium_refresh_time()) # wait a short time before checking again
        sleep(self.settle_time()) # wait for sample temperature to reach sensor temperature

    def __set_and_equilibrate_temp(self, temp):
        self.temp_setpoint(temp)
        self.__stabilise_temperature()

    def __set_auto_pressure_value(self, pressure):
        self.pressure_setpoint(pressure)
        self.automatic_flow(True)
        
class MontanaInstruments_Cryostation(IPInstrument):
    """
    Class to represent a Montana Instruments Cryostation.
    """

    def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            port: Optional[int] = None,
            terminator: str = '\r\n',
            timeout: float = 20,
            **kwargs: Any):
        super().__init__(name, address=address, port=port,
                         terminator=terminator, timeout=timeout, **kwargs)

        #self._heater_range_auto = False
        #self._heater_range_temp = [0.03, 0.1, 0.3, 1, 12, 40]
        #self._heater_range_curr = [0.316, 1, 3.16, 10, 31.6, 100]
        #self._control_channel = 5
        #self._max_field = 14

        self.add_parameter(name='temp_setpoint',
                           unit='K',
                           label='Temperature setpoint',
                           get_cmd='GTSP',
                           set_cmd='STSP{:f}',
                           get_parser=float,
                           vals=Numbers(min_value=2, max_value=295),
                           instrument=self
                           )
        
        self.add_parameter(name='temp_sample',
                           unit='K',
                           label='Temperature sample',
                           get_cmd='GST',
                           get_parser=float,
                           instrument=self
                           )
        
        self.add_parameter(name='temp_platform',
                           unit='K',
                           label='Temperature platform',
                           get_cmd='GPT',
                           get_parser=float,
                           instrument=self
                           )
        
        self.add_parameter(name='temp_stage1',
                           unit='K',
                           label='Temperature Stage 1',
                           get_cmd='GS1T',
                           get_parser=float,
                           instrument=self)
        
        self.add_parameter(name='temp_stage2',
                           unit='K',
                           label='Temperature Stage 2',
                           get_cmd='GS2T',
                           get_parser=float,
                           instrument=self)
        
        self.add_parameter(name='power_heater_platform',
                           unit='W',
                           label='Platform heater power',
                           get_cmd='GPHP',
                           get_parser=float,
                           instrument=self)
        
        self.add_parameter(name='power_heater_stage1',
                           unit='W',
                           label='Stage 1 heater power',
                           get_cmd='GS1HP',
                           get_parser=float,
                           instrument=self)
        
        self.add_parameter(name='temp_stability',
                           unit='K',
                           label='temperature stability sample stage',
                           get_cmd='GSS',
                           get_parser=float,
                           instrument=self
                           )
        
        self.connect_message()
        
        
    def get_idn(self) -> Dict[str, Optional[str]]:
        """ Return the Instrument Identifier Message """
        idstr = self.ask('*IDN?')
        idparts = [p.strip() for p in idstr.split(':', 4)][1:]
        
    def start_cooldown(self):
        self.write('SCD')
        
    def standby(self):
        self.write('SSB')
        
    def stop_automation(self):
        self.write('STP')
        
    def start_warmup(self):
        self.write('SWU')
        
    def set_temp_and_wait(self, setpoint):
        self.temp_setpoint.set(setpoint)
        time.sleep(10)
        while self.temp_stability.get() > 0.2:
            time.sleep(10)
        return self.temp_setpoint.get()
        
    def wait_stability(self, time=10):
        stability = self.temp_stability.get()
        while stability > 0.02 or stability < 0:
            time.sleep(time)
            stabilit = self.temp_stability.get()
        
    def get_alltemp(self):
        self.power_heater_platform.get()
        self.temp_platform.get()
        self.temp_stability.get()
        self.temp_sample.get()
        self.temp_setpoint.get()
        self.temp_stage1.get()
        self.temp_stage2.get()