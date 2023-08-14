import enum
import ctypes
import ctypes.util
import os
import serial
from typing import Tuple, Optional, Union, List
from pyvisa.resources.serial import SerialInstrument

import qcodes.utils.validators as vals
from qcodes import Instrument, Parameter, VisaInstrument

from qcodes_contrib_drivers.drivers.Thorlabs.APT import Thorlabs_APT, ThorlabsHWType
from . import _Thorlabs_error_codes as _error_codes

class HomeDirection(enum.Enum):
    """Constants for the home direction of Thorlabs KDC101"""
    FORWARD = "fwd"
    REVERSE = "rev"


class HomeLimitSwitch(enum.Enum):
    """Constants for the home limit switch of Thorlabs KDC101"""
    REVERSE = "rev"
    FORWARD = "fwd"
    
class StageUnits(enum.Enum):
    """Constants for the stage unit of Thorlabs KDC101"""
    UNITS_MM = "mm"
    UNITS_DEG = "deg"
    
class HardwareLimitSwitch(enum.Enum):
    """Constants for the hardware limit switch settings of Thorlabs KDC101"""
    IGNORE = "ignore"
    MAKES = "makes"
    BREAKS = "breakes"
    MAKES_HOMEONLY = "makes_homeonly"
    BREAKS_HOMEONLY = "breaks_homeonly"
    
class MoveDirection(enum.Enum):
    """Constants for the moving direction of Thorlabs KDC101 (used with move_velocity)"""
    FORWARD = "fwd"
    REVERSE = "rev"
    
class ProfileMode(enum.Enum):
    """Constants for the profile mode settings of Thorlabs KDC101"""
    TRAPEZOIDAL = "trapezoidal"
    SCURVE = "scurve"
    
class JoystickDirectionSense(enum.Enum):
    """Constants for the Joystick direction sense settings"""
    POSITIVE = "pos"
    NEGATIVE = "neg"
    
def _get_error_text(error_code):
    """returns an error text for the specified error code for Thorlabs KDC101"""
    if (error_code == 0):
        return "Command successful."
    else:
        try:
            return _error_codes.error_message[error_code]
        except:
            raise KeyError("Invalid error code")
    


class Thorlabs_general(Instrument):
    """
    General Instrument driver for Thorlabs

    Args:
        name: Instrument name.
        device_id: ID for the desired rotator.
        apt: Thorlabs APT server.
        type: Thorlabs Type

    Attributes:
        apt: Thorlabs APT server.
        serial_number: Serial number of the device.
        model: Model description.
        version: Firmware version.
    """

    def __init__(self, name: str, device_id: int, apt: Thorlabs_APT, **kwargs):
        super().__init__(name, **kwargs)

        # Save APT server reference
        self.apt = apt
        self.id = int(device_id)
        self.serial_number = int(device_id)

        # initialization
        #self.serial_number = self.apt.get_hw_serial_num_ex(self.type.value, self.id)
        self.apt.init_hw_device(self.serial_number)
        self.model, self.version, self.label = self.apt.get_hw_info(self.serial_number)
        self.type = ThorlabsHWType[self.model]

        # Set velocity and move-home parameters to previous values. Otherwise the velocity is very
        # very low and it is not the velocity stored in the parameters... For whatever reason?
        self._set_velocity_parameters()
        self._set_home_parameters()

        # Helpers
        homedirection_val_mapping = {HomeDirection.FORWARD: 1,
                                 HomeDirection.FORWARD.value: 1,
                                 HomeDirection.REVERSE: 2,
                                 HomeDirection.REVERSE.value: 2}
        homelim_switch_val_mapping = {HomeLimitSwitch.REVERSE: 1,
                                  HomeLimitSwitch.REVERSE.value: 1,
                                  HomeLimitSwitch.FORWARD: 4,
                                  HomeLimitSwitch.FORWARD.value: 4}
        stage_units_val_mapping = {StageUnits.UNITS_MM: 1,
                                   StageUnits.UNITS_MM.value: 1,
                                   StageUnits.UNITS_DEG: 2,
                                   StageUnits.UNITS_DEG.value: 2}
        hardlim_switch_val_mapping = {HardwareLimitSwitch.IGNORE: 1,
                                      HardwareLimitSwitch.IGNORE.value: 1,
                                      HardwareLimitSwitch.MAKES: 2,
                                      HardwareLimitSwitch.MAKES.value: 2,
                                      HardwareLimitSwitch.BREAKS: 3,
                                      HardwareLimitSwitch.BREAKS.value: 3,
                                      HardwareLimitSwitch.MAKES_HOMEONLY: 4,
                                      HardwareLimitSwitch.MAKES_HOMEONLY.value: 4,
                                      HardwareLimitSwitch.BREAKS_HOMEONLY: 5,
                                      HardwareLimitSwitch.BREAKS_HOMEONLY.value: 5}
        movedirection_val_mapping = {MoveDirection.FORWARD: 1,
                                     MoveDirection.FORWARD.value: 1,
                                     MoveDirection.REVERSE: 2,
                                     MoveDirection.REVERSE.value: 2}
        profilemode_val_mapping = {ProfileMode.TRAPEZOIDAL: 0,
                                   ProfileMode.TRAPEZOIDAL.value: 0,
                                   ProfileMode.SCURVE: 2,
                                   ProfileMode.SCURVE.value: 2}
        joystickdirection_val_mapping = {JoystickDirectionSense.POSITIVE: 1,
                                         JoystickDirectionSense.POSITIVE.value: 1,
                                         JoystickDirectionSense.NEGATIVE: 2,
                                         JoystickDirectionSense.NEGATIVE.value: 2}
        

        # PARAMETERS
        # Position
        self.position = Parameter(
            "position",
            get_cmd=self._get_position,
            set_cmd=self._set_position,
            vals=vals.Numbers(0, 360),
            unit=u"\u00b0",
            label="Position"
        )
        
        self.position_async = Parameter(
            "position_async",
            get_cmd=None,
            set_cmd=self._set_position_async,
            vals=vals.Numbers(0, 360),
            unit=u"\u00b0",
            label="Position"
        )
        
        # Velocity
        
        self.velocity_min = Parameter(
            "velocity_min",
            set_cmd = self._set_velocity_min,
            get_cmd = self._get_velocity_min,
            vals=vals.Numbers(0, 25),
            unit=u"\u00b0/s",
            label="Minimum Velocity",
        )
        
        self.velocity_acceleration = Parameter(
            "velocity_acceleration",
            set_cmd=self._set_velocity_acceleration,
            get_cmd=self._get_velocity_acceleration,
            vals=vals.Numbers(0, 25),
            unit=u"\u00b0/s\u00b2",
            label="Acceleration"
        )
        
        self.velocity_max = Parameter(
            "velocity_max",
            set_cmd=self._set_velocity_max,
            get_cmd=self._get_velocity_max,
            vals=vals.Numbers(0, 25),
            unit=u"\u00b0/s",
            label="Maximum Velocity"
        )

        # Move home parameters
        self.move_home_direction = Parameter(
            "move_home_direction",
            set_cmd=self._set_home_direction,
            get_cmd=self._get_home_direction,
            val_mapping=homedirection_val_mapping,
            label="Direction for Moving Home"
        )
        
        self.move_home_velocity = Parameter(
            "move_home_velocity",
            set_cmd=self._set_home_velocity,
            get_cmd=self._get_home_velocity,
            vals=vals.Numbers(0, 25),
            unit=u"\u00b0/s",
            label="Velocity for Moving Home"
        )
        
        self.move_home_zero_offset = Parameter(
            "move_home_zero_offset",
            set_cmd=self._set_home_zero_offset,
            get_cmd=self._get_home_zero_offset,
            vals=vals.Numbers(0, 360),
            unit=u"\u00b0",
            label="Zero Offset for Moving Home"
        )

        # FUNCTIONS
        # Stop motor
        self.add_function("stop",
                          call_cmd=self._stop,
                          args=[])

        # Moving direction
        self.add_function("move_direction",
                          call_cmd=self._move_direction,
                          args=[vals.Enum(*homedirection_val_mapping)],
                          arg_parser=lambda val: homedirection_val_mapping[val])

        # Enable/disable
        self.add_function("enable",
                          call_cmd=self._enable,
                          args=[])
        self.add_function("disable",
                          call_cmd=self._disable,
                          args=[])

        # Move home
        self.add_function("move_home",
                          call_cmd=self._move_home,
                          args=[])
        self.add_function("move_home_async",
                          call_cmd=self._move_home_async,
                          args=[])

        # print connect message
        self.connect_message()

    def get_idn(self):
        """Returns hardware information of the device."""
        return {"vendor": "Thorlabs", "model": self.model,
                "firmware": self.version, "serial": self.serial_number}

    def _get_position(self) -> float:
        return self.apt.mot_get_position(self.serial_number)

    def _set_position(self, position: float):
        self.apt.mot_move_absolute_ex(self.serial_number, position, True)

    def _set_position_async(self, position: float):
        self.apt.mot_move_absolute_ex(self.serial_number, position, False)

    def _get_velocity_parameters(self) -> Tuple[float, float, float]:
        return self.apt.mot_get_velocity_parameters(self.serial_number)

    def _set_velocity_parameters(self,
                                 min_vel: Optional[float] = None, accn: Optional[float] = None, max_vel: Optional[float] = None):
        if min_vel is None or accn is None or max_vel is None:
            old_min_vel, old_accn, old_max_vel = self._get_velocity_parameters()
            if min_vel is None:
                min_vel = old_min_vel
            if accn is None:
                accn = old_accn
            if max_vel is None:
                max_vel = old_max_vel
        return self.apt.mot_set_velocity_parameters(self.serial_number, min_vel, accn, max_vel)

    def _get_velocity_min(self) -> float:
        min_vel, _, _ = self._get_velocity_parameters()
        return min_vel

    def _set_velocity_min(self, min_vel: float):
        self._set_velocity_parameters(min_vel=min_vel)

    def _get_velocity_acceleration(self) -> float:
        _, accn, _ = self._get_velocity_parameters()
        return accn

    def _set_velocity_acceleration(self, accn: float):
        self._set_velocity_parameters(accn=accn)

    def _get_velocity_max(self) -> float:
        _, _, max_vel = self._get_velocity_parameters()
        return max_vel

    def _set_velocity_max(self, max_vel: float):
        self._set_velocity_parameters(max_vel=max_vel)

    def _get_home_parameters(self) -> Tuple[int, int, float, float]:
        return self.apt.mot_get_home_parameters(self.serial_number)

    def _set_home_parameters(self, direction: Optional[int] = None, lim_switch: Optional[int] = None,
                             velocity: Optional[float] = None, zero_offset: Optional[float] = None):
        if direction is None or lim_switch is None or velocity is None or zero_offset is None:
            old_direction, old_lim_switch, old_velocity, old_zero_offset = self._get_home_parameters()
            if direction is None:
                direction = old_direction
            if lim_switch is None:
                lim_switch = old_lim_switch
            if velocity is None:
                velocity = old_velocity
            if zero_offset is None:
                zero_offset = old_zero_offset

        return self.apt.mot_set_home_parameters(self.serial_number,
                                                direction, lim_switch, velocity, zero_offset)

    def _get_home_direction(self) -> int:
        direction, _, _, _ = self._get_home_parameters()
        return direction

    def _set_home_direction(self, direction: int):
        self._set_home_parameters(direction=direction)

    def _get_home_lim_switch(self) -> int:
        _, lim_switch, _, _ = self._get_home_parameters()
        return lim_switch

    def _set_home_lim_switch(self, lim_switch: int):
        self._set_home_parameters(lim_switch=lim_switch)

    def _get_home_velocity(self) -> float:
        _, _, velocity, _ = self._get_home_parameters()
        return velocity

    def _set_home_velocity(self, velocity: float):
        self._set_home_parameters(velocity=velocity)

    def _get_home_zero_offset(self) -> float:
        _, _, _, zero_offset = self._get_home_parameters()
        return zero_offset

    def _set_home_zero_offset(self, zero_offset: float):
        self._set_home_parameters(zero_offset=zero_offset)

    def _stop(self):
        self.apt.mot_stop_profiled(self.serial_number)

    def _move_direction(self, direction: int):
        self.apt.mot_move_velocity(self.serial_number, direction)

    def _enable(self):
        self.apt.enable_hw_channel(self.serial_number)

    def _disable(self):
        self.apt.disable_hw_channel(self.serial_number)

    def _move_home(self):
        self.apt.mot_move_home(self.serial_number, True)

    def _move_home_async(self):
        self.apt.mot_move_home(self.serial_number, False)
        
        
class ThorlabsHWType(enum.Enum):
    BSC001 = 11 # 1 ch benchtop stepper driver
    BSC101 = 12 # 1 ch benchtop stepper driver
    BSC002 = 13 # 2 ch benchtop stepper driver
    BDC101 = 14 # 1 ch benchtop dc servo driver
    SCC001 = 21 # 1 ch stepper driver card (used within BSC102, 103 units)
    DCC001 = 22 # 1 ch DC servo driver card (used within BDC102, 103 units)
    ODC001 = 24 # 1 ch DC servo driver cube
    OST001 = 25 # 1 ch stepper driver cube
    MST601 = 26 # 2 ch modular stepper driver module
    TST001 = 29 # 1 ch stepper driver T-cube
    TDC001 = 31 # 1 ch DC servo driver T-cube
    LTSXXX = 42 # LTS300/LTS150 long travel integrated driver/stages
    L490MZ = 43 # L490MZ Integrated Driver/Labjack
    BBD10X = 44 # 1/2/3 ch benchtop brushless DC servo driver
    MFF10X = 48 # # motorized filter flip
    K10CR1 = 50 # steper motor rotation mount
    KDC101 = 63 # 1 ch Brushed DC servo motor controller K-cube
    
    
class _Thorlabs_APT(Thorlabs_APT):
    # default dll installation path
    _dll_path = 'C:\\Program Files\\Thorlabs\\APT\\APT Server\\APT.dll'
    # success and error codes
    _success_code = 0
    def __init__(self, dll_path: Optional[str] = None, verbose: bool = False, event_dialog: bool = False):
        if (os.name != 'nt'):
            raise Exception("Your operating system is not supported. " \
                "The Thorlabs API currently only works on Windows.")
        #lib = None
        #filename = ctypes.util.find_library('APT')
        #if filename is not None:
        #    lib = ctypes.windll.LoadLibrary(filename)
        #else:
        #    filename = "%s/APT.dll"%os.path.dirname(__file__)
        #    lib = ctypes.windll.LoadLibrary(filename)
        #    if lib is None:
        #        filename = "%s/APT.dll"%os.path.dirname(sys.argv[0])
        #        lib = ctypes.windll.LoadLibrary(filename)
        #        if lib is None:
        #            raise Exception("could not find the APT.dll library")
        #self.dll = lib
        # save attributes
        self.verbose = verbose

        # connect to the DLL
        self.dll = ctypes.CDLL(dll_path or self._dll_path)

        # initialize APT server
        self.apt_init()
        self.enable_event_dlg(event_dialog)

        
    def list_available_devices(self, hw_type: Union[int, ThorlabsHWType, None] = None) \
            -> List[Tuple[int, int, int]]:
        """Lists all available Thorlabs devices, that can connect to the APT server.

        Args:
            hw_type: If this parameter is passed, the function only searches for a certain device
                     model. Otherwise (if the parameter is None), it searches for all Thorlabs
                     devices.

        Returns:
            A list of tuples. Each list-element is a tuple of 3 ints, containing the device's
            hardware type, device id and serial number: [(hw type id, device id, serial), ...]
        """
        devices = []
        count = ctypes.c_long()

        if hw_type is not None:
            # Only search for devices of the passed hardware type (model)
            if isinstance(hw_type, ThorlabsHWType):
                hw_type_range = [hw_type.value]
            else:
                hw_type_range = [int(hw_type)]
        else:
            # Search for all models
            hw_type_range = list(range(100))

        for hw_type_id in hw_type_range:
            # Get number of devices of the specific hardware type
            if self.dll.GetNumHWUnitsEx(hw_type_id, ctypes.byref(count)) == 0 and count.value > 0:
                # Is there any device of the specified hardware type
                serial_number = ctypes.c_long()
                # Get the serial numbers of all devices of that hardware type
                for ii in range(count.value):
                    if self.dll.GetHWSerialNumEx(hw_type_id, ii, ctypes.byref(serial_number)) == 0:
                        devices.append((hw_type_id, ii, serial_number.value))

        return devices
    
    def get_hw_serial_num_ex(self, hw_type: Union[int, ThorlabsHWType], index: int) -> int:
        """Returns the a device's serial number by passing the model's hardware type and the
        device id.

        Args:
            hw_type: Hardware type (model code) to search for.
            index: Device id

        Returns:
            The device's serial number
        """
        if isinstance(hw_type, ThorlabsHWType):
            hw_type_id = hw_type.value
        else:
            hw_type_id = int(hw_type)

        c_hw_type = ctypes.c_long(hw_type_id)
        c_index = ctypes.c_long(index)
        c_serial_number = ctypes.c_long()

        code = self.dll.GetHWSerialNumEx(c_hw_type, c_index, ctypes.byref(c_serial_number))
        self.error_check(code, 'GetHWSerialNumEx')

        return c_serial_number.value


class arduino2ch_stage(VisaInstrument):
    """
    Class to represent a 2-channel arduino controller (X-Y stage)
    """
    default_timeout = 1.0

    def __init__(self, name: str, address: str, reverse_x=False, reverse_y=False, **kwargs) -> None:
        """
        Args:
            name (str): Name to use internally
            address (str): VISA string describing the serial port,
            for example "ASRL3" for COM3.
        """
        super().__init__(name, address, timeout=self.default_timeout,
                         terminator='\n',**kwargs)
        assert isinstance(self.visa_handle, SerialInstrument)
        self.visa_handle.baud_rate = 9600
        
        self._path = "C:/arduinoXYstage/"
        self._path_x = self._path + "stepper_position_x.txt"
        self._path_y = self._path + "stepper_position_y.txt"
        self.metadata = {}
        
        self.x = Parameter(
            "x",
            unit="m",
            get_cmd=self.get_x,
            get_parser=float,
            set_cmd=self.set_x,
            set_parser=float,
            instrument=self
        )
        
        self.y = Parameter(
            "y",
            unit="m",
            get_cmd=self.get_y,
            get_parser=float,
            set_cmd=self.set_y,
            set_parser=float,
            instrument=self
        )
        
        self.init_device(reverse_x, reverse_y)
        self.connect_message()
        
    def init_device(self, reverse_x: bool, reverse_y: bool):
        """initialize device

        Args:
            reverse_x (bool): reverse direction for x
            reverse_y (bool): reverse direction for y
        """
        
        if not os.path.isfile(self._path_x):
            self._write_file(self._path_x, 0)
        if not os.path.isfile(self._path_y):
            self._write_file(self._path_y, 0)
            
        if reverse_x:
            self.x_p = 'n'
            self.x_n = 'p'
        else:
            self.x_p = 'p'
            self.x_n = 'n'
        if reverse_y:
            self.y_p = 'n'
            self.y_n = 'p'
        else:
            self.y_p = 'p'
            self.y_n = 'n'

        
    def get_position(self):
        x = self.get_x()
        y = self.get_y()
        return float(x), float(y)
    
    def set_position(self, x, y):
        self.set_x(x)
        self.set_y(y)
    
    def go_to_home(self):
        self.set_position(0,0)
    
    def set_home(self):
        self._write_file(self._path_x,0)
        self._write_file(self._path_y,0)
        self.get_position()
        return
    
    def set_x(self, val):
        val = float(val*1e6)
        if val >=0 and val <= 300:
            max_steps_X = 19100
            max_um_X = 300
            new_pos = round(max_steps_X*val/max_um_X)
            
            old_pos = self._read_file(self._path_x)
            old_pos = float(old_pos)
            
            if new_pos - old_pos < 0:
                shift = (new_pos - old_pos - 1000)
                self._go_x_steps(shift)
                self._go_x_steps(1000)
            else:
                shift = new_pos - old_pos
                self._go_x_steps(shift)
                
            self._write_file(self._path_x,new_pos)
        else:
            print('position must be between 0 and 300um')
            
    def set_y(self, val):
        val = float(val*1e6)
        if val >=0 and val <= 300:
            max_steps_Y = 19100
            max_um_Y = 300
            new_pos = round(max_steps_Y*val/max_um_Y)
            
            old_pos = self._read_file(self._path_y)
            old_pos = float(old_pos)
            
            if new_pos - old_pos < 0:
                shift = (new_pos - old_pos - 1000)
                self._go_y_steps(shift)
                self._go_y_steps(1000)
            else:
                shift = new_pos - old_pos
                self._go_y_steps(shift)
                
            self._write_file(self._path_y,new_pos)
        else:
            print('position must be between 0 and 300um')
            
    def get_x(self):
        max_steps_X = 19100
        max_um_X = 300
        X_in_um = (float(self._read_file(self._path_x))*max_um_X)/max_steps_X
        return X_in_um/1e6
    
    def get_y(self):
        max_steps_Y = 19100
        max_um_Y = 300
        Y_in_um = (float(self._read_file(self._path_y))*max_um_Y)/max_steps_Y
        return Y_in_um/1e6

    def _go_x_steps(self, steps):
        if steps >= 0:
            ss = 'x' + self.x_p + str(abs(steps))
        else:
            ss = 'x' + self.x_n + str(abs(steps))
        self.visa_handle.write(ss)
        finished = None
        while finished != "0":
            finished = self.visa_handle.read_bytes(1)
            
    def _go_y_steps(self, steps):
        if steps >= 0:
            ss = 'y' + self.y_p + str(abs(steps))
        else:
            ss = 'y' + self.y_n + str(abs(steps))
        self.visa_handle.write(ss)
        finished = None
        while finished != "0":
            finished = self.visa_handle.read_bytes(1)
            
    def _read_file(self, path):
        file = open(path, 'r')
        val = file.read()
        file.close()
        return val
    
    def _write_file(self, path, val):
        file = open(path, 'w+')
        val = file.write(str(val))
        file.close()
        
    def get_idn(self):
        return { "vendor": "arduino 2ch", "model": None,
                "serial": None, "firmware": None,}
        
        
class arduino1ch_stage(Instrument):
    """
    Class to represent a 1-channel arduino controller (Z stage)
    """
    def __init__(self, name: str, address: str, reverse_z: bool = False, **kwargs) -> None:
        """
        Args:
            name (str): Name to use internally
            address (str): VISA resource address
            reverse_z (bool)
        """
        super().__init__(name, address, **kwargs)
        self._path = "C:/arduinoXYstage/"
        self._path_x = self._path + "stepper_position_dummy.txt"
        self._path_y = self._path + "stepper_position_y.txt"
    
        
        self.z = Parameter(
            "z",
            unit="m",
            get_cmd=self.get_z,
            get_parser=float,
            set_cmd=self.set_z,
            set_parser=float,
            instrument=self
        )
        
        self.connect_message()
        
    def init_device(self, reverse_z: bool):
        """initialize device

        Args:
            reverse_x (bool): reverse direction for x
            reverse_y (bool): reverse direction for y
        """
        
        try:
            self._ser = getattr(serial,self._address)
        except AttributeError:
            self._ser = serial.Serial(port=self._address, baudrate=9600, timeout=0.01)
            setattr(serial, self._address, self._ser)
        
        if self._ser.isOpen():
            print('Serial port is open')
        else:
            raise ValueError('wrong serial port')
        
        if not os.path.isfile(self._path_x):
            self._write_file(self._path_x, 0)
        if not os.path.isfile(self._path_y):
            self._write_file(self._path_y, 0)
            
        if reverse_z:
            self.z_p = 'n'
            self.z_n = 'p'
        else:
            self.z_p = 'p'
            self.z_n = 'n'

        
    def get_position(self):
        z = self.get_z()
        return float(z)
    
    def set_position(self, z):
        self.set_z(z)
    
    def go_to_home(self):
        self.set_position(0)
    
    def set_home(self):
        self._write_file(self._path_x,0)
        self._write_file(self._path_y,0)
        self.get_position()
        return
    
    def set_z(self, val):
        val = val*1e6
        if val >=0 and val <= 300:
            max_steps_Z = 19100
            max_um_Z = 300
            new_pos = round(max_steps_Z*val/max_um_Z)
            
            old_pos = self._read_file(self._path_y)
            old_pos = float(old_pos)
            
            if new_pos - old_pos < 0:
                shift = (new_pos - old_pos - 1000)
                self._go_z_steps(shift)
                self._go_z_steps(1000)
            else:
                shift = new_pos - old_pos
                self._go_z_steps(shift)
                
            self._write_file(self._path_z,new_pos)
        else:
            print('position must be between 0 and 300um')
            
    def get_z(self):
        max_steps_Z = 19100
        max_um_Z = 300
        Z_in_um = (float(self._read_file(self._path_y))*max_um_Z)/max_steps_Z
        return Z_in_um/1e6
            
    def _go_j_steps(self, steps):
        if steps >= 0:
            ss = 'y' + self.z_p + str(abs(steps))
        else:
            ss = 'y' + self.z_n + str(abs(steps))
        self._ser.write(str.encode(ss))
        finished = None
        while finished != "0":
            finished = self._ser.read(1)
            
    def _read_file(self, path):
        file = open(path, 'r')
        val = file.read()
        file.close()
        return val
    
    def _write_file(self, path, val):
        file = open(path, 'w+')
        val = file.write(str(val))
        file.close()