import logging
import time
import os
import ctypes
from typing import Optional, Tuple, Any

from qcodes import Instrument, Parameter, VisaInstrument
from qcodes.utils.validators import Ints

log = logging.getLogger(__name__)
# --------------
# Photodetectors
# --------------


class Thorlab_PM100D(VisaInstrument):
    """
    Class to represent a Thorlab PM100D photodetector
    """
    def __init__(self,
                 name: str,
                 address: Optional[str] = None,
                 timeout: float = 20,
                 **kwargs: Any):
        """
        Args:
            name (str): name for the instrument
            address (Optional[str], optional): Visa address. Defaults to None.
            timeout (float, optional). Defaults to 20.
        """
        super().__init__(name, address, terminator='\n', **kwargs)
        self._timeout = timeout
        self._timeout_pwr = 120

        self.averaging = Parameter(
            "averaging",
            get_cmd='AVER?',
            get_parser=int,
            set_cmd='AVER',
            set_parser=int,
            instrument=self
        )

        self.wavelength = Parameter(
            "wavelength",
            get_cmd='SENS:CORR:WAV?',
            get_parser=float,
            set_cmd='SENS:CORR:WAV',
            set_parser=float,
            instrument=self
        )

        self.power = Parameter(
            "power",
            unit="W",
            get_cmd=self._get_power,
            get_parser=float,
            instrument=self
        )

        self.write('STAT:OPER:PTR 512')
        self.write('STAT:OPER:NTR 0')
        self.ask('STAT:OPER?')
        self._check_error()
        self.averaging(300)
        self._set_conf_power()

        self.connect_message()

    def _check_error(self) -> None:
        err = self.ask('SYST:ERR?')
        if(err[:2] != '+0'):
            raise RuntimeError(f'PM100D call failed with error: {err}')

    def _set_conf_power(self) -> None:
        """Set configuration to power mode
        """
        self.write('CONF:POW')  # set config to power mode
        self.ask('ABOR;:STAT:OPER?')
        self.write('INIT')

    def _get_power(self) -> float:
        """Get the power
        """
        self._set_conf_power()
        oper = self.ask('STAT:OPER?')
        start = time.process_time()
        ts = 0
        while oper != str(512) and ts < self._timeout_pwr:
            oper = self.ask('STAT:OPER?')
            ts = (time.process_time()-start)
        power = self.ask('FETC?')
        self._check_error()
        return power

# -------------
# Light sources
# -------------


class DRSDaylightSolutions_MIRcat(Instrument):

    _GET_STATUS = {
        0: 'unarmed',
        1: 'armed and not emitting',
        2: 'armed and emitting'
    }

    def __init__(self,
                 name: str,
                 MIRcat_libraries: Optional[str] = "C:\\MIRcat_laser\\libs\\x64\\"):
        self._MIRcat_path = MIRcat_libraries
        super().__init__(name)

        os.chdir(self._MIRcat_path)
        self._dll = ctypes.CDLL(self._MIRcat_path + "MIRcatSDK.dll")

        # get MIRcat API version
        self._major = ctypes.c_uint16()
        self._minor = ctypes.c_uint16()
        self._patch = ctypes.c_uint16()
        # Initialise MIRcatSDK & connect
        self._dll.MIRcatSDK_Initialize()

        self._is_interlock_set = ctypes.c_bool(False)
        self._is_keyswitch_set = ctypes.c_bool(False)
        self._num_qcl = ctypes.c_uint8()
        # get number of installed QCLs
        self._dll.MIRcatSDK_GetNumInstalledQcls(ctypes.byref(self._num_qcl))
        # check interlock status
        self._dll.MIRcatSDK_IsInterlockedStatusSet(
            ctypes.byref(self._is_interlock_set)
        )
        # check key switch status
        self._dll.MIRcatSDK_IsKeySwitchStatusSet(
            ctypes.byref(self._is_keyswitch_set)
        )

        # parameters

        self.status = Parameter(
            "status",
            set_cmd=self._set_status,
            get_cmd=self._get_status,
            vals=Ints(0, 2),
            instrument=self
        )

        self.wavelength = Parameter(
            "wavelength",
            get_cmd=self._get_wavelength,
            get_parser=float,
            set_cmd=self._set_wavelength,
            set_parser=float,
            unit='m',
            instrument=self
        )

        self.wavenumber = Parameter(
            "wavenumber",
            get_cmd=self._get_wavenumber,
            get_parser=float,
            set_cmd=self._set_wavenumber,
            set_parser=float,
            unit='cm-1',
            instrument=self
        )

        self.chip = Parameter(
            "chip",
            get_cmd=self._get_chip,
            get_parser=int,
            instrument=self
        )

        self.T1 = Parameter(
            "T1",
            label="temperature chip 1",
            get_cmd=self._get_temperature_1,
            get_parser=float,
            unit='°C',
            instrument=self
        )
        self.T2 = Parameter(
            "T2",
            label="temperature chip 2",
            get_cmd=self._get_temperature_2,
            get_parser=float,
            unit='°C',
            instrument=self
        )
        self.T3 = Parameter(
            "T3",
            label="temperature chip 3",
            get_cmd=self._get_temperature_3,
            get_parser=float,
            unit='°C',
            instrument=self
        )
        self.T4 = Parameter(
            "T4",
            label="temperature chip 4",
            get_cmd=self._get_temperature_4,
            get_parser=float,
            unit='°C',
            instrument=self
        )

        self.pulse_rate_1 = Parameter(
            "pulse_rate_1",
            label="pulse rate chip 1",
            get_cmd=self._get_pulse_rate_1,
            get_parser=float,
            set_cmd=self._set_pulse_rate_1,
            set_parser=float,
            unit='Hz',
            instrument=self
        )
        self.pulse_rate_2 = Parameter(
            "pulse_rate_2",
            label="pulse rate chip 2",
            get_cmd=self._get_pulse_rate_2,
            get_parser=float,
            set_cmd=self._set_pulse_rate_2,
            set_parser=float,
            unit='Hz',
            instrument=self
        )
        self.pulse_rate_3 = Parameter(
            "pulse_rate_3",
            label="pulse rate chip 3",
            get_cmd=self._get_pulse_rate_3,
            get_parser=float,
            set_cmd=self._set_pulse_rate_3,
            set_parser=float,
            unit='Hz',
            instrument=self
        )
        self.pulse_rate_4 = Parameter(
            "pulse_rate_4",
            label="pulse rate chip 4",
            get_cmd=self._get_pulse_rate_4,
            get_parser=float,
            set_cmd=self._set_pulse_rate_4,
            set_parser=float,
            unit='Hz',
            instrument=self
        )

        self.pulse_width_1 = Parameter(
            "pulse_width_1",
            label="pulse width chip 1",
            get_cmd=self._get_pulse_width_1,
            get_parser=float,
            set_cmd=self._set_pulse_width_1,
            set_parser=float,
            unit='s',
            instrument=self
        )
        self.pulse_width_2 = Parameter(
            "pulse_width_2",
            label="pulse width chip 2",
            get_cmd=self._get_pulse_width_2,
            get_parser=float,
            set_cmd=self._set_pulse_width_2,
            set_parser=float,
            unit='s',
            instrument=self
        )
        self.pulse_width_3 = Parameter(
            "pulse_width_3",
            label="pulse width chip 3",
            get_cmd=self._get_pulse_width_3,
            get_parser=float,
            set_cmd=self._set_pulse_width_3,
            set_parser=float,
            unit='s',
            instrument=self
        )
        self.pulse_width_4 = Parameter(
            "pulse_width_4",
            label="pulse width chip 4",
            get_cmd=self._get_pulse_width_4,
            get_parser=float,
            set_cmd=self._set_pulse_width_4,
            set_parser=float,
            unit='s',
            instrument=self
        )

        self.pulse_current_1 = Parameter(
            "pulse_current_1",
            label="pulse current chip 1",
            get_cmd=self._get_pulse_current_1,
            get_parser=float,
            set_cmd=self._set_pulse_current_1,
            set_parser=float,
            unit='A',
            instrument=self
        )
        self.pulse_current_2 = Parameter(
            "pulse_current_2",
            label="pulse current chip 2",
            get_cmd=self._get_pulse_current_2,
            get_parser=float,
            set_cmd=self._set_pulse_current_2,
            set_parser=float,
            unit='A',
            instrument=self
        )
        self.pulse_current_3 = Parameter(
            "pulse_current_3",
            label="pulse current chip 3",
            get_cmd=self._get_pulse_current_3,
            get_parser=float,
            set_cmd=self._set_pulse_current_3,
            set_parser=float,
            unit='A',
            instrument=self
        )
        self.pulse_current_4 = Parameter(
            "pulse_current_4",
            label="pulse current chip 4",
            get_cmd=self._get_pulse_current_4,
            get_parser=float,
            set_cmd=self._set_pulse_current_4,
            set_parser=float,
            unit='A',
            instrument=self
        )

        self._set_pulse_width(400, 1)  # parameters chip 1
        self._set_pulse_rate(3.5e5, 1)

        self._set_pulse_width(400, 2)  # parameters chip 2
        self._set_pulse_rate(5e5, 2)

        self._set_pulse_width(400, 3)  # parameters chip 3
        self._set_pulse_rate(3.5e5, 3)

        self._set_pulse_width(200, 4)  # parameters chip 4
        self._set_pulse_rate(2.5e5, 4)

        self.connect_message()

    def get_temperatures(self) -> tuple:
        T1 = self.T1()
        T2 = self.T2()
        T3 = self.T3()
        T4 = self.T4()
        return (T1, T2, T3, T4)

        print(f'Temperature chip 1: {T1}°C\n')
        print(f'Temperature chip 2: {T2}°C\n')
        print(f'Temperature chip 3: {T3}°C\n')
        print(f'Temperature chip 4: {T4}°C\n')

    def get_idn(self) -> dict:
        idparts = [
            'DRS Daylight Solutions', 'MIRcat',
            None, self._get_api_version()
        ]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_api_version(self) -> str:
        self._dll.MIRcatSDK_GetAPIVersion(
            ctypes.byref(self._major),
            ctypes.byref(self._minor),
            ctypes.byref(self._patch))
        return f'{self._major.value}.{self._minor.value}.{self._patch.value}'

    def _get_status(self) -> str:
        self.log.info('get status')
        is_armed = ctypes.c_bool(True)
        is_emitting = ctypes.c_bool(True)
        self._dll.MIRcatSDK_IsLaserArmed(ctypes.byref(is_armed))
        time.sleep(0.05)
        self._dll.MIRcatSDK_IsEmissionOn(ctypes.byref(is_emitting))
        res = int(is_armed) + int(is_emitting)
        return self._GET_STATUS[res]

    def _set_status(self, mode: int) -> None:
        """
        Args:
            mode (int): see dictionary of allowed values _GET_SATUS
        """
        if mode in self._GET_STATUS.keys():
            self.log.info(f'set device remote status to {self._GET_STATUS[mode]}')
            is_armed = ctypes.c_bool()
            is_emitting = ctypes.cbool()
            self._dll.MIRcatSDK_IsLaserArmed(ctypes.byref(is_armed))
            time.sleep(0.05)
            self._dll.MIRcatSDK_IsEmissionOn(ctypes.byref(is_emitting))
            state = int(is_armed.value) + int(is_emitting.value)

            if not state and mode:
                self.arm()
                time.sleep(.05)
                if mode == 2:
                    self._dll.MIRcatSDK_TurnEmissionOn()
            elif not mode and state:
                if state == 2:
                    self._dll.MIRcatSDK_TurnEmissionOff()
                    time.sleep(.05)
                self._dll.MIRcatSDK_DisarmLaser()
                time.sleep(.05)
            elif mode == 2 and state == 1:
                self._dll.MIRcatSDK_TurnEmissionOn()
                time.sleep(.05)
            elif mode == 1 and state == 2:
                self._dll.MIRcatSDK_TurnEmissionOff()
                time.sleep(.05)
        else:
            print('Invalid mode inserted.')

    def _get_wavelength(self) -> float:
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        self._dll.MIRcatSDK_GetActualWW(
            ctypes.byref(actual_ww),
            ctypes.byref(units),
            ctypes.byref(light_valid)
        )
        self._dll.MIRcatSDK_GetTuneWW(
            ctypes.byref(tuned_ww),
            ctypes.byref(units),
            ctypes.byref(qcl)
        )
        return actual_ww.value/1e6

    def _get_wavenumber(self):
        """check the wavenumber"""
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        self._dll.MIRcatSDK_GetActualWW(
            ctypes.byref(actual_ww),
            ctypes.byref(units),
            ctypes.byref(light_valid)
        )
        self._dll.MIRcatSDK_GetTuneWW(
            ctypes.byref(tuned_ww),
            ctypes.byref(units),
            ctypes.byref(qcl)
        )
        if actual_ww.value < 6:
            wavenum = 1e4/tuned_ww.value  # from um to cm-1
        else:
            wavenum = 1e4/actual_ww.value
        return wavenum

    def _get_temperature(self, chip: int) -> float:
        temp = ctypes.c_float()
        ret = self._dll.MIRcatSDK_GetQCLTemperature(
            chip, ctypes.byref(temp)
        )
        if not ret:
            return temp.value
        else:
            return ValueError(f'Error checking temperature, ret = {ret}')
        
    def _get_temperature_1(self) -> float:
        return self._get_temperature(chip=1)
    def _get_temperature_2(self) -> float:
        return self._get_temperature(chip=2)
    def _get_temperature_3(self) -> float:
        return self._get_temperature(chip=3)
    def _get_temperature_4(self) -> float:
        return self._get_temperature(chip=4)

    def _get_pulse_rate(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_rate = ctypes.c_float()
        return self._dll.MIRcatSDK_GetQCLPulseRate(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_rate)
        ).value
        
    def _get_pulse_rate_1(self) -> float:
        return self._get_pulse_rate(chip=1)
    def _get_pulse_rate_2(self) -> float:
        return self._get_pulse_rate(chip=2)
    def _get_pulse_rate_3(self) -> float:
        return self._get_pulse_rate(chip=3)
    def _get_pulse_rate_4(self) -> float:
        return self._get_pulse_rate(chip=4)

    def _get_pulse_width(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_width = ctypes.c_float()
        ret = self._dll.MIRcatSDK_GetQCLPulseWidth(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_width)
        )
        return ret.value/1e9
    
    def _get_pulse_width_1(self) -> float:
        return self._get_pulse_width(chip=1)
    def _get_pulse_width_2(self) -> float:
        return self._get_pulse_width(chip=2)
    def _get_pulse_width_3(self) -> float:
        return self._get_pulse_width(chip=3)
    def _get_pulse_width_4(self) -> float:
        return self._get_pulse_width(chip=4)

    def _get_pulse_current(self, chip: int = 0) -> float:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_current = ctypes.c_float()
        ret = self._dll.MIRcatSDK_GetQCLCurrent(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_current)
        )
        return ret.value/1e3
    
    def _get_pulse_current_1(self) -> float:
        return self._get_pulse_current(chip=1)
    def _get_pulse_current_2(self) -> float:
        return self._get_pulse_current(chip=2)
    def _get_pulse_current_3(self) -> float:
        return self._get_pulse_current(chip=3)
    def _get_pulse_current_4(self) -> float:
        return self._get_pulse_current(chip=4)

    def get_pulse_parameters(self, chip: int = 0) -> float:
        tup = (
            self._get_pulse_rate(self, chip=chip),
            self._get_pulse_width(self, chip=chip),
            self._get_pulse_current(self, chip=chip)
        )
        return tup

    def _get_chip(self) -> int:
        """check the active chip"""
        actual_ww = ctypes.c_float()
        units = ctypes.c_uint8()
        light_valid = ctypes.c_bool()
        tuned_ww = ctypes.c_float()
        chip = ctypes.c_uint8()
        self._dll.MIRcatSDK_GetActualWW(
            ctypes.byref(actual_ww),
            ctypes.byref(units),
            ctypes.byref(light_valid)
        )
        self._dll.MIRcatSDK_GetTuneWW(
            ctypes.byref(tuned_ww),
            ctypes.byref(units),
            ctypes.byref(chip)
        )
        time.sleep(.05)
        return chip.value

    def _set_pulse_rate(self, pulse_rate: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_width = ctypes.c_float()
        pulse_current = ctypes.c_float()

        self._dll.MIRcatSDK_GetQCLPulseWidth(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_width)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_GetQCLCurrent(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_current)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_SetQCLParams(
            ctypes.c_uint8(chip),
            ctypes.c_float(pulse_rate),
            ctypes.c_float(pulse_width.value),
            ctypes.c_float(pulse_current.value)
        )
    
    def _set_pulse_rate_1(self, pulse_rate: float) -> None:
        return self._set_pulse_rate(pulse_rate, chip=1)
    def _set_pulse_rate_2(self, pulse_rate: float) -> None:
        return self._set_pulse_rate(pulse_rate, chip=2)
    def _set_pulse_rate_3(self, pulse_rate: float) -> None:
        return self._set_pulse_rate(pulse_rate, chip=3)
    def _set_pulse_rate_4(self, pulse_rate: float) -> None:
        return self._set_pulse_rate(pulse_rate, chip=4)

    def _set_pulse_width(self, pulse_width: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_rate = ctypes.c_float()
        pulse_current = ctypes.c_float()

        self._dll.MIRcatSDK_GetQCLPulseRate(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_rate)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_GetQCLCurrent(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_current)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_SetQCLParams(
            ctypes.c_uint8(chip),
            ctypes.c_float(pulse_rate.value),
            ctypes.c_float(pulse_width*1e9),
            ctypes.c_float(pulse_current.value)
        )
        
    def _set_pulse_width_1(self, pulse_width: float) -> None:
        return self._set_pulse_width(pulse_width, chip=1)
    def _set_pulse_width_2(self, pulse_width: float) -> None:
        return self._set_pulse_width(pulse_width, chip=2)
    def _set_pulse_width_3(self, pulse_width: float) -> None:
        return self._set_pulse_width(pulse_width, chip=3)
    def _set_pulse_width_4(self, pulse_width: float) -> None:
        return self._set_pulse_width(pulse_width, chip=4)

    def _set_pulse_current(self, pulse_current: float, chip: int = 0) -> None:
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value

        pulse_rate = ctypes.c_float()
        pulse_width = ctypes.c_float()

        self._dll.MIRcatSDK_GetQCLPulseRate(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_rate)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_GetQCLPulseWidth(
            ctypes.c_uint8(chip),
            ctypes.byref(pulse_width)
        )
        time.sleep(.05)
        self._dll.MIRcatSDK_SetQCLParams(
            ctypes.c_uint8(chip),
            ctypes.c_float(pulse_rate.value),
            ctypes.c_float(pulse_width.value),
            ctypes.c_float(pulse_current*1e3)
        )
        
    def _set_pulse_current_1(self, pulse_current: float) -> None:
        return self._set_pulse_current(pulse_current, chip=1)
    def _set_pulse_current_2(self, pulse_current: float) -> None:
        return self._set_pulse_current(pulse_current, chip=2)
    def _set_pulse_current_3(self, pulse_current: float) -> None:
        return self._set_pulse_current(pulse_current, chip=3)
    def _set_pulse_current_4(self, pulse_current: float) -> None:
        return self._set_pulse_current(pulse_current, chip=4)

    def _set_wavelength(self, wavelength: float, chip: int = 0) -> None:
        wavelength = wavelength*1e6
        if chip == 0:
            if wavelength <= 8.2:
                chip = 1
            elif 8.2 < wavelength <= 10.3:
                chip = 2
            elif 10.3 < wavelength <= 12.7:
                chip = 3
            else:
                chip = 4

        self._dll.MIRcatSDK_TuneToWW(
            ctypes.c_float(wavelength),
            ctypes.c_ubyte(1),
            ctypes.c_uint8(chip)
        )
        self._get_wavenumber(chip=chip)

    def _set_wavenumber(self, wavenumber: float, chip: int = 0) -> None:
        if chip == 0:
            if wavenumber >= 1219:
                chip = 1
            elif 971 <= wavenumber < 1219:
                chip = 2
            elif 788 <= wavenumber < 971:
                chip = 3
            else:
                chip = 4

        self._dll.MIRcatSDK_TuneToWW(
            ctypes.c_float(wavenumber),
            ctypes.c_ubyte(2),
            ctypes.c_uint8(chip)
        )
        self._get_wavelength(chip=chip)

    def set_pulse_parameters(self,
                             pulse_rate: float,
                             pulse_width: float,
                             current: float,
                             chip: int) -> None:
        """Set pulse parameters

        Args:
            pulse_rate (float): pulse rate in Hz
            pulsewidth (float): pulse width in s
            current (float): current in A
        """
        self._dll.MIRcatSDK_SetQCLParams(
            ctypes.c_uint8(chip),
            ctypes.c_float(pulse_rate),
            ctypes.c_float(pulse_width*1e9),
            ctypes.c_float(current*1e3)
        )

    def get_limits(self, chip: int = 0) -> tuple:
        """Get the limits for a qcl chip

        Args:
            chip (int, optional). Defaults to =0.

        Returns:
            tuple: (pulse_rate_max (Hz), pulse_width_max (s), duty_cycle_max,
            current_max(A))
        """
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value
        pulse_rate_max = ctypes.c_float()
        pulse_width_max = ctypes.c_float()
        duty_cycle_max = ctypes.c_uint16()
        current_max = ctypes.c_float()

        self._dll.MIRcatSDK_GetQCLPulseLimits(
            chip,
            ctypes.byref(pulse_rate_max),
            ctypes.byref(pulse_width_max),
            ctypes.byref(duty_cycle_max)
        )
        self._dll.MIRcatSDK_GetQCLMaxPulsedCurrent(
            chip,
            ctypes.byref(current_max)
        )
        return (pulse_rate_max.value, pulse_width_max.value/1e9,
                duty_cycle_max.value, current_max.value/1e3)
        
    def arm(self) -> None:
        at_temperature = ctypes.c_bool(False)
        is_armed = ctypes.c_bool(False)
        self._dll.MIRcatSDK_IsLaserArmed(ctypes.byref(is_armed))
        if not is_armed.value:
            self._dll.MIRcatSDK_ArmDisarmLaser()
            
        while not is_armed.value:
            self._dll.MIRcatSDK_IsLaserArmed(ctypes.byref(is_armed))
            time.sleep(1)
            
        self._dll.MIRcatSDK_AreTECsAtSetTemperature(ctypes.byref(at_temperature))
        tec_current = ctypes.c_uint16(0)
        qcl_temp = ctypes.c_float(0)
        
        while not at_temperature.value:
            for i in range(0, self._num_qcl.value):
                self._dll.MIRcatSDK_GetQCLTemperature(
                    ctypes.c_uint8(i+1),
                    ctypes.byref(qcl_temp)
                )
                self._dll.MIRcatSDK_GetTecCurrent(
                    ctypes.c_uint8(i+1),
                    ctypes.byref(tec_current)
                )
            self._dll.MIRcatSDK_AreTECsAtSetTemperature(ctypes.byref(at_temperature))
            time.sleep(.1)
        #return at_temperature.value

    def get_ranges(self, chip: int = 0) -> tuple:
        """Get the acceptable range

        Args:
            chip (int, optional). Defaults to 0.

        Returns:
            tuple: (pf_min_range (m), pf_max_range (m))
        """
        if chip == 0:
            units = ctypes.c_uint8()
            tuned_ww = ctypes.c_float()
            chip = ctypes.c_uint8()
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(chip))
            chip = chip.value
        pf_min_range = ctypes.c_float()
        pf_max_range = ctypes.c_float()
        pb_units = ctypes.c_uint8()

        self._dll.MIRcatSDK_GetQclTuningRange(
            chip,
            ctypes.byref(pf_min_range),
            ctypes.byref(pf_max_range),
            ctypes.byref(pb_units)
        )
        return (pf_min_range*1e6, pf_max_range*1e6)

    def check_tune(self) -> float:
        is_tuned = ctypes.c_bool(False)
        tuned_ww = ctypes.c_float()
        qcl = ctypes.c_uint8()
        units = ctypes.c_uint8()
        while not is_tuned.value:
            self._dll.MIRcatSDK_IsTuned(ctypes.byref(is_tuned))
            self._dll.MIRcatSDK_GetTuneWW(
                ctypes.byref(tuned_ww),
                ctypes.byref(units),
                ctypes.byref(qcl)
            )
        if units == ctypes.c_ubyte(1):
            return tuned_ww.value*1e-6
        elif units == ctypes.c_ubyte(2):
            return 1e2/tuned_ww.value  # convert from cm-1 to m


def _extract_tuple(val: int) -> Tuple:
    res = []
    lst = [1, 1, 0, 0]
    while lst:
        num = lst.pop()
        diff = val - num
        if diff in lst:
            res.append((diff, num))
    return res[0]
