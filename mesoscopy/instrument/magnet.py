import configparser
import re
from functools import partial
import pyvisa
import logging
from traceback import format_exc
from typing import Optional, Any, Union, List, Dict
from numpy import array

from qcodes import IPInstrument, VisaInstrument, Parameter
from qcodes.instrument.parameter import _BaseParameter
from qcodes.utils.validators import Enum, Ints, Numbers, Bool
from qcodes.utils.helpers import create_on_off_val_mapping
from qcodes_contrib_drivers.drivers.Oxford.IPS120 import OxfordInstruments_IPS120

from time import sleep


# ---------------------------------
# functions to be used with magnets
# ---------------------------------


def calibrate_magnet(param_set: _BaseParameter,
                     mag_range: float | None = None,
                     swr: float = .15) -> None:
    if mag_range is None:
        mag_range = param_set.root_instrument._max_field
    param_set.root_instrument.magnet_sweeprate(swr)
    while abs(mag_range) > 1e-5:
        param_set(mag_range)
        print(f'sweeping magnet to {mag_range}T at {swr}T/min')
        sleep(abs(mag_range)/swr*60+10)
        mag_range = -mag_range/2
    param_set(0)


# --------------
# magnet drivers
# --------------


class Triton(IPInstrument):
    """
    Triton Driver, based on the one provided by QCoDes
    CHANGES: changing Bx, By or Bz is done instantly, and the measurement can
    continue immediately after that. useful for maps.
    Changing B: sleep the time to change.
    """

    def __init__(
            self,
            name: str,
            address: Optional[str] = None,
            port: Optional[int] = None,
            terminator: str = '\r\n',
            tmpfile: Optional[str] = None,
            timeout: float = 20,
            **kwargs: Any):
        super().__init__(name, address=address, port=port,
                         terminator=terminator, timeout=timeout, **kwargs)

        self._heater_range_auto = False
        self._heater_range_temp = [0.03, 0.1, 0.3, 1, 12, 40]
        self._heater_range_curr = [0.316, 1, 3.16, 10, 31.6, 100]
        self._control_channel = 5
        self._max_field = 14

        self.add_parameter(name='time',
                           label='System Time',
                           get_cmd='READ:SYS:TIME',
                           get_parser=self._parse_time)

        self.add_parameter(name='action',
                           label='Current action',
                           get_cmd='READ:SYS:DR:ACTN',
                           get_parser=self._parse_action)

        self.add_parameter(name='status',
                           label='Status',
                           get_cmd='READ:SYS:DR:STATUS',
                           get_parser=self._parse_status)

        self.add_parameter(name='pid_control_channel',
                           label='PID control channel',
                           get_cmd=self._get_control_channel,
                           set_cmd=self._set_control_channel,
                           vals=Ints(1, 16))

        self.add_parameter(name='pid_mode',
                           label='PID Mode',
                           get_cmd=partial(self._get_control_param, 'MODE'),
                           set_cmd=partial(self._set_control_param, 'MODE'),
                           val_mapping={'on':  'ON', 'off': 'OFF'})

        self.add_parameter(name='pid_ramp',
                           label='PID ramp enabled',
                           get_cmd=partial(self._get_control_param,
                                           'RAMP:ENAB'),
                           set_cmd=partial(self._set_control_param,
                                           'RAMP:ENAB'),
                           val_mapping={'on':  'ON', 'off': 'OFF'})

        self.add_parameter(name='pid_setpoint',
                           label='PID temperature setpoint',
                           unit='K',
                           get_cmd=partial(self._get_control_param, 'TSET'),
                           set_cmd=partial(self._set_control_param, 'TSET'))

        self.add_parameter(name='pid_rate',
                           label='PID ramp rate',
                           unit='K/min',
                           get_cmd=partial(self._get_control_param,
                                           'RAMP:RATE'),
                           set_cmd=partial(self._set_control_param,
                                           'RAMP:RATE'))

        self.add_parameter(name='pid_range',
                           label='PID heater range',
                           unit='mA',
                           get_cmd=partial(self._get_control_param, 'RANGE'),
                           set_cmd=partial(self._set_control_param, 'RANGE'),
                           vals=Enum(*self._heater_range_curr))

        self.add_parameter(name='magnet_status',
                           label='Magnet status',
                           unit='',
                           get_cmd=partial(self._get_control_B_param, 'ACTN'))

        self.add_parameter(name='magnet_sweeprate',
                           label='Magnet sweep rate',
                           unit='T/min',
                           get_cmd=partial(
                               self._get_control_B_param, 'RVST:RATE'),
                           set_cmd=partial(
                               self._set_control_magnet_sweeprate_param))

        self.add_parameter(name='magnet_sweeprate_insta',
                           label='Instantaneous magnet sweep rate',
                           unit='T/min',
                           get_cmd=partial(self._get_control_B_param, 'RFST'))

        self.add_parameter(name='B',
                           label='Magnetic field',
                           unit='T',
                           get_cmd=partial(self._get_control_B_param, 'VECT'))

        self.add_parameter(name='Bx',
                           label='Magnetic field x-component',
                           unit='T',
                           get_cmd=partial(
                               self._get_control_Bcomp_param, 'VECTBx'),
                           set_cmd=partial(self._set_control_Bx_param))

        self.add_parameter(name='By',
                           label='Magnetic field y-component',
                           unit='T',
                           get_cmd=partial(
                               self._get_control_Bcomp_param, 'VECTBy'),
                           set_cmd=partial(self._set_control_By_param))

        self.add_parameter(name='Bz',
                           label='Magnetic field z-component',
                           unit='T',
                           get_cmd=partial(
                               self._get_control_Bcomp_param, 'VECTBz'),
                           set_cmd=partial(self._set_control_Bz_param))

        self.add_parameter(name='magnet_sweep_time',
                           label='Magnet sweep time',
                           unit='T/min',
                           get_cmd=partial(self._get_control_B_param,
                                           'RVST:TIME'))

        self.add_parameter(name='magnet_swhtr',
                           label='Magnet persistent switch heater',
                           set_cmd=self._set_swhtr,
                           get_cmd='READ:SYS:VRM:SWHT',
                           get_parser=self._parse_swhtr,
                           vals=Enum(*val_bool))

        self.add_parameter(name='magnet_POC',
                           label='Persistent after completing sweep?',
                           set_cmd='SET:SYS:VRM:POC:{}',
                           get_cmd='READ:SYS:VRM:POC',
                           get_parser=self._parse_state,
                           vals=Enum(*val_bool))

        self.add_parameter(name='MC_heater',
                           label='Mixing chamber heater power',
                           unit='uW',
                           get_cmd='READ:DEV:H1:HTR:SIG:POWR',
                           set_cmd='SET:DEV:H1:HTR:SIG:POWR:{}',
                           get_parser=self._parse_htr,
                           set_parser=float,
                           vals=Numbers(0, 300000))

        self.add_parameter(name='still_heater',
                           label='Still heater power',
                           unit='uW',
                           get_cmd='READ:DEV:H2:HTR:SIG:POWR',
                           set_cmd='SET:DEV:H2:HTR:SIG:POWR:{}',
                           get_parser=self._parse_htr,
                           set_parser=float,
                           vals=Numbers(0, 300000))

        self.add_parameter(name='turbo_speed',
                           unit='Hz',
                           get_cmd='READ:DEV:TURB1:PUMP:SIG:SPD',
                           get_parser=self._parse_pump_speed)

        self.add_parameter(name='temp_setpoint',
                           unit='K',
                           get_cmd=partial(self._get_control_param, 'TSET'),
                           set_cmd=self.ramp_temperature_to)

        self.chan_alias = {'MC': 'T8', 'MC_cernox': 'T5', 'still': 'T3',
                           'cold_plate': 'T4', 'magnet': 'T13', 'PT2h': 'T1',
                           'PT2p': 'T2', 'PT1h': 'T6', 'PT1p': 'T7'}
        self.chan_temp_names: Dict[str, Dict[str, Optional[str]]] = {}
        if tmpfile is not None:
            self._get_temp_channel_names(tmpfile)

        try:
            self._get_named_channels()
        except:
            logging.warning('Ignored an error in _get_named_channels\n' +
                            format_exc())
        self._get_named_temp_channels()
        self._get_temp_channels()
        self._get_pressure_channels()
        self._get_valve_channels()
        self._get_pump_channels()
        self.connect_message()

    def set_B(self, x: float, y: float, z: float, s: float) -> None:
        if 0 < s <= 0.2:
            self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                       ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) +
                       ']\r\n')
            self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
            t_wait = self.magnet_sweep_time() * 60 + 10
            print('Please wait ' + str(t_wait) +
                  ' seconds for the field sweep...')
            sleep(t_wait)
        else:
            print('Warning: set magnet sweep rate in range (0 , 0.2] T/min')

    def read_valves(self):
        for i in range(1, 10):
            print('V{}:  {}'.format(i, getattr(self, 'V%d' % i)()))

    def read_pumps(self):
        print(f'Turbo: {self.turbo()},  speed: {self.turbo_speed()} Hz')
        print(f'KNF: {self.knf()}')
        print(f'Forepump: {self.forepump()}')

    def read_temps(self):
        for i in self.chan_alias:
            stat = 'off'
            if getattr(self, i + '_temp_enable')() == 0:
                stat = 'off'
            elif getattr(self, i + '_temp_enable')() == 1:
                stat = 'on'
            else:
                print('temperature reading status not determined')
            print(f'{i} - {stat}: {getattr(self, self.chan_alias[i])()} K')

    def read_pressures(self):
        for i in range(1, 6):
            print(f'P{i}: {getattr(self, "P"+str(i))()}')
        print(f'POVC: {getattr(self, "POVC")()}')

    def temp_disable_enable_MC_magnet(self):
        for i in self.chan_alias:
            if i not in ('MC', 'magnet'):
                getattr(self, i + '_temp_enable')('off')
            else:
                getattr(self, i + '_temp_enable')('on')

    def temp_disable_enable_MC(self):
        for i in self.chan_alias:
            if i == 'MC':
                getattr(self, i + '_temp_enable')('on')
            else:
                getattr(self, i + '_temp_enable')('off')

    def temp_enable_MCcernox(self):
        for i in self.chan_alias:
            if i == 'MC_cernox':
                getattr(self, i + '_temp_enable')('on')

    def temp_disable_all(self):
        for i in self.chan_alias:
            getattr(self, i + '_temp_enable')('on')

    def magnet_hold(self):
        '''stops any magnet sweep'''
        self.write('SET:SYS:VRM:ACTN:HOLD')

    def get_PID(self):
        cmd = 'READ:DEV:5:TEMP:LOOP:'
        P = self._get_response_value(self.ask(cmd + 'P'))
        I = self._get_response_value(self.ask(cmd + 'I'))
        D = self._get_response_value(self.ask(cmd + 'D'))
        return P, I, D

    def set_PID(self, p: int, i: int, d: int) -> None:
        cmd = 'SET:DEV:5:TEMP:LOOP:'
        self.write(cmd + 'P:' + str(p))
        self.write(cmd + 'I:' + str(i))
        self.write(cmd + 'D:' + str(d))

    def _autoselect_pid(self, temp_init: float, temp_target: float = 0):
        if temp_init <= 1.2 or temp_target <= 1.2:
            self.set_PID(15, 120, 0)
        else:
            self.set_PID(3, 10, 0)
    # TODO: this doesn't take into account transition stage.
    # TODO: remove temp init and integrate in the function?

    def _autoselect_sensor(self, temp_init: float, temp_target: float = 0):
        if temp_init <= 1.6 or temp_target <= 1.6:
            self._set_control_channel(8)
        else:
            self._set_control_channel(5)
        # TODO: don't do in term of control channel number, but with the type
        # of control channel

    def _autoselect_heater_range(self, temp_init: float) -> None:
        rangetemp = array(self._heater_range_temp)
        tempcondition = (temp_init < rangetemp)
        htr_range = [self._heater_range_curr[i]
                     for i in range(len(rangetemp)) if tempcondition[i]]
        self._set_control_param('RANGE', min(htr_range))

    def _autoselect_turbo(self, temp: float):
        if temp > .8:
            self.write('SET:DEV:TURB1:PUMP:SIG:STATE:OFF')
        else:
            self.write('SET:DEV:TURB1:PUMP:SIG:STATE:ON')

    def _autoselect_stillhtr(self, temp: float):
        if temp > 2:
            self.write('SET:DEV:H2:HTR:SIG:POWR:0')
        else:
            self.condense()

    def _autoselect_valves(self, temp: float):
        if temp > 2:
            self.write('SET:DEV:9:VALV:SIG:STATE:CLOSE')
            self.write('SET:DEV:4:VALV:SIG:STATE:OPEN')
        else:
            self.write('SET:DEV:4:VALV:SIG:STATE:CLOSE')
            self.write('SET:DEV:9:VALV:SIG:STATE:OPEN')

    def ramp_temperature_to(self, value: float) -> None:
        chan_number = self._get_control_channel()
        chan = 'T' + str(chan_number)
        temp_init = self.parameters[chan]()

        rangetemp = array([0, .005, .03, .06, .09, .12, .3, .6, .8, 1.2,
                           1.6, 1.8, 2, 4, 6, 8, 10, 40])
        tempcondition = (temp_init < rangetemp)*(value > rangetemp)

        for i in range(len(rangetemp)):
            if tempcondition[i]:
                chan_number = self._get_control_channel()
                chan = 'T' + str(chan_number)
                temp_instant = self.parameters[chan]()
                self._autoselect_pid(rangetemp[i-1], rangetemp[i])
                self._autoselect_sensor(rangetemp[i-1], rangetemp[i])
                self._autoselect_turbo(temp_instant)
                self._autoselect_stillhtr(temp_instant)
                self._autoselect_valves(temp_instant)
                self.pid_setpoint(rangetemp[i])
                self._autoselect_heater_range(temp_instant)
                while self.parameters[chan]() < .95*rangetemp[i]:
                    sleep(10)
                if rangetemp[i] == .8:
                    print('Wait 5min at the lambda point')
                    sleep(300)
                elif rangetemp[i] == 2:
                    print('Wait 10 min while He3 is boiling')
                    sleep(600)
        chan_number = self._get_control_channel()
        chan = 'T' + str(chan_number)
        temp_instant = self.parameters[chan]()
        self._autoselect_id(temp_instant, value)
        self._autoselect_sensor(temp_instant, value)
        self._autoselect_heater_range(value)
        self._autoselect_turbo(value)
        self._autoselect_stillhtr(value)
        self._autoselect_valves(value)
        self.pid_setpoint(value)
        while self.parameters[chan]() < .98*value:
            sleep(5)
        print(f'T = {value} reached')

    def _get_control_B_param(
            self,
            param: str
    ) -> Optional[Union[float, str, List[float]]]:
        cmd = f'READ:SYS:VRM:{param}'
        return self._get_response_value(self.ask(cmd))

    def _get_control_Bcomp_param(
            self,
            param: str
    ) -> Optional[Union[float, str, List[float]]]:
        cmd = f'READ:SYS:VRM:{param}'
        return self._get_response_value(self.ask(cmd[:-2]) + cmd[-2:])

    def _get_response(self, msg: str) -> str:
        return msg.split(':')[-1]

    def _get_response_value(
            self,
            msg: str
    ) -> Optional[Union[float, str, List[float]]]:
        msg = self._get_response(msg)
        if msg.endswith('NOT_FOUND'):
            return None
        elif msg.endswith('IDLE'):
            return 'IDLE'
        elif msg.endswith('RTOS'):
            return 'RTOS'
        elif msg.endswith('Bx'):
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0])
        elif msg.endswith('By'):
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[1])
        elif msg.endswith('Bz'):
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[2])
        elif len(re.findall(r"[-+]?\d*\.\d+|\d+", msg)) > 1:
            return [float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0]),
                    float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[1]),
                    float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[2])]
        try:
            return float(re.findall(r"[-+]?\d*\.\d+|\d+", msg)[0])
        except Exception:
            return msg

    def get_idn(self) -> Dict[str, Optional[str]]:
        """ Return the Instrument Identifier Message """
        idstr = self.ask('*IDN?')
        idparts = [p.strip() for p in idstr.split(':', 4)][1:]

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_control_channel(self, force_get: bool = False) -> int:

        # verify current channel
        if self._control_channel and not force_get:
            tempval = self.ask(
                f'READ:DEV:T{self._control_channel}:TEMP:LOOP:MODE')
            if not tempval.endswith('NOT_FOUND'):
                return self._control_channel

        # either _control_channel is not set or wrong
        for i in range(1, 17):
            tempval = self.ask(f'READ:DEV:T{i}:TEMP:LOOP:MODE')
            if not tempval.endswith('NOT_FOUND'):
                self._control_channel = i
                break
        return self._control_channel

    def _set_control_channel(self, channel: int) -> None:
        self._control_channel = channel
        self.write('SET:DEV:T{}:TEMP:LOOP:HTR:H1'.format(
            self._get_control_channel()))

    def _get_control_param(
            self,
            param: str
    ) -> Optional[Union[float, str, List[float]]]:
        chan = self._get_control_channel()
        cmd = f'READ:DEV:T{chan}:TEMP:LOOP:{param}'
        return self._get_response_value(self.ask(cmd))

    def _set_control_param(self, param: str, value: float) -> None:
        chan = self._get_control_channel()
        cmd = f'SET:DEV:T{chan}:TEMP:LOOP:{param}:{value}'
        self.write(cmd)

    def _set_control_magnet_sweeprate_param(self, s: float) -> None:
        if 0 < s <= 0.21:
            x = round(self.Bx(), 4)
            y = round(self.By(), 4)
            z = round(self.Bz(), 4)
            self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                       ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) +
                       ']\r\n')
        else:
            print(
                'Warning: set sweeprate in range (0 , 0.21] T/min, not setting'
                ' sweeprate')

    def _set_control_Bx_param(self, x: float) -> None:
        s = self.magnet_sweeprate()
        y = round(self.By(), 4)
        z = round(self.Bz(), 4)
        self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                   ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
        self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
        # just to give an time estimate, +10s for overhead
        t_wait = self.magnet_sweep_time() * 60 + 10
        print('It will take ' + str(t_wait) + ' s for the field sweep...')
        # while self.magnet_status() != 'IDLE':
        #    pass

    def _set_control_By_param(self, y: float) -> None:
        s = self.magnet_sweeprate()
        x = round(self.Bx(), 4)
        z = round(self.Bz(), 4)
        self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                   ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
        self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
        # just to give an time estimate, +10s for overhead
        t_wait = self.magnet_sweep_time() * 60 + 10
        print('It will take ' + str(t_wait) + ' s for the field sweep...')
        # while self.magnet_status() != 'IDLE':
        #     pass

    def _set_control_Bz_param(self, z: float) -> None:
        s = self.magnet_sweeprate()
        x = round(self.Bx(), 4)
        y = round(self.By(), 4)
        self.write('SET:SYS:VRM:COO:CART:RVST:MODE:RATE:RATE:' + str(s) +
                   ':VSET:[' + str(x) + ' ' + str(y) + ' ' + str(z) + ']\r\n')
        self.write('SET:SYS:VRM:ACTN:RTOS\r\n')
        # just to give an time estimate, +10s for overhead
        t_wait = self.magnet_sweep_time() * 60 + 10
        print('It will take ' + str(t_wait) + ' s for the field sweep...')
        # while self.magnet_status() != 'IDLE':
        #     pass

    def _get_named_channels(self) -> None:
        allchans_str = self.ask('READ:SYS:DR:CHAN')
        allchans = allchans_str.replace('STAT:SYS:DR:CHAN:', '', 1).split(':')
        for ch in allchans:
            msg = 'READ:SYS:DR:CHAN:%s' % ch
            rep = self.ask(msg)
            if 'INVALID' not in rep and 'NONE' not in rep:
                alias, chan = rep.split(':')[-2:]
                self.chan_alias[alias] = chan
                self.add_parameter(name=alias,
                                   unit='K',
                                   get_cmd='READ:DEV:%s:TEMP:SIG:TEMP' % chan,
                                   get_parser=self._parse_temp)

    def _get_temp_channel_names(self, file: str) -> None:
        config = configparser.ConfigParser()
        with open(file, encoding='utf16') as f:
            next(f)
            config.read_file(f)

        for section in config.sections():
            options = config.options(section)
            namestr = '"m_lpszname"'
            if namestr in options:
                chan_number = int(section.split('\\')[-1].split('[')[-1]) + 1
                # the names used in the register file are base 0 but the api
                # and the gui uses base one names so add one
                chan = 'T' + str(chan_number)
                name = config.get(section, '"m_lpszname"').strip("\"")
                self.chan_temp_names[chan] = {'name': name, 'value': None}

    def _set_swhtr(self, val):
        val = _parse_bool(val, 'ON', 'OFF')
        if val == 'ON':
            self.write('SET:SYS:VRM:ACTN:NPERS')
            print('Wait 5 min for the switch to warm')
            sleep(10)
            while self.magnet_status() != 'IDLE':
                pass
        elif val == 'OFF':
            self.write('SET:SYS:VRM:ACTN:PERS')
            print('Wait 5 min for the switch to cool')
            sleep(10)
            while self.magnet_status() != 'IDLE':
                pass
        else:
            raise ValueError('Should be a boolean value (ON, OFF)')

    def _get_named_temp_channels(self):
        for al in tuple(self.chan_alias):
            chan = self.chan_alias[al]
            self.add_parameter(name=al+'_temp',
                               unit='K',
                               get_cmd='READ:DEV:%s:TEMP:SIG:TEMP' % chan,
                               get_parser=self._parse_temp)
            self.add_parameter(name=al+'_temp_enable',
                               get_cmd='READ:DEV:%s:TEMP:MEAS:ENAB' % chan,
                               get_parser=self._parse_state,
                               set_cmd='SET:DEV:%s:TEMP:MEAS:ENAB:{}' % chan,
                               vals=Enum(*val_bool))
            if al == 'MC':
                self.add_parameter(name='MC_Res',
                                   unit='Ohms',
                                   get_cmd='READ:DEV:%s:TEMP:SIG:RES' % chan,
                                   get_parser=self._parse_res)

    def _get_pressure_channels(self):
        self.chan_pressure = []
        for i in range(1, 6):
            chan = 'P%d' % i
            self.chan_pressure.append(chan)
            self.add_parameter(name=chan,
                               unit='mbar',
                               get_cmd='READ:DEV:%s:PRES:SIG:PRES' % chan,
                               get_parser=self._parse_pres)

        chan = 'P6'
        self.chan_pressure.append('POVC')
        self.add_parameter(name='POVC',
                           unit='mbar',
                           get_cmd='READ:DEV:%s:PRES:SIG:PRES' % chan,
                           get_parser=self._parse_pres)
        self.chan_pressure = set(self.chan_pressure)

    def _get_valve_channels(self):
        self.chan_valves = []
        for i in range(1, 10):
            chan = 'V%d' % i
            self.chan_valves.append(chan)
            self.add_parameter(name=chan,
                               get_cmd='READ:DEV:%s:VALV:SIG:STATE' % chan,
                               set_cmd='SET:DEV:%s:VALV:SIG:STATE:{}' % chan,
                               get_parser=self._parse_valve_state,
                               vals=Enum('OPEN', 'CLOSE', 'TOGGLE'))
        self.chan_valves = set(self.chan_valves)

    def _get_pump_channels(self):
        self.chan_pumps = ['turbo', 'knf', 'forepump']
        self.add_parameter(name='turbo',
                           get_cmd='READ:DEV:TURB1:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:TURB1:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           vals=Enum(*val_bool))
        self.add_parameter(name='knf',
                           get_cmd='READ:DEV:COMP:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:COMP:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           vals=Enum(*val_bool))
        self.add_parameter(name='forepump',
                           get_cmd='READ:DEV:FP:PUMP:SIG:STATE',
                           set_cmd='SET:DEV:FP:PUMP:SIG:STATE:{}',
                           get_parser=self._parse_state,
                           vals=Enum(*val_bool))
        self.chan_pumps = set(self.chan_pumps)

    def _get_temp_channels(self) -> None:
        chan_temps_list = []
        for i in range(1, 17):
            chan = 'T%d' % i
            chan_temps_list.append(chan)
            self.add_parameter(name=chan,
                               unit='K',
                               get_cmd='READ:DEV:%s:TEMP:SIG:TEMP' % chan,
                               get_parser=self._parse_temp)
        self.chan_temps = set(chan_temps_list)

    def fullcooldown(self, force=False):
        '''Starts the full cooldown automation'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:CLDN')
        elif force:
            self.write('SET:SYS:DR:ACTN:CLDN')

    def condense(self, force=False):
        '''Starts condensing (use only if T < 12K)'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:COND')
        elif force:
            self.write('SET:SYS:DR:ACTN:COND')

    def mixture_collect(self, force=False):
        '''Starts collecting the mixture into the tank'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:COLL')
        elif force:
            self.write('SET:SYS:DR:ACTN:COLL')

    def precool(self, force=False):
        '''Starts a pre-cool'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:PCL')
        elif force:
            self.write('SET:SYS:DR:ACTN:PCL')

    def pause_precool(self, force=False):
        '''Pauses the pre-cool automation'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:PCOND')
        elif force:
            self.write('SET:SYS:DR:ACTN:PCOND')

    def resume_precool(self, force=False):
        '''Resumes the pre-cool automation'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:RCOND')
        elif force:
            self.write('SET:SYS:DR:ACTN:RCOND')

    def empty_precool(self, force=False):
        '''Starts the empty pre-cool circuit automation'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:EPCL')
        elif force:
            self.write('SET:SYS:DR:ACTN:EPCL')

    def stopcool(self, force=False):
        '''Stops any running automation'''
        self.write('SET:SYS:ACTN:STOP')

    def warmup(self, force=False):
        '''starts the system warm-up automation'''
        if _checkquench(self):
            self.write('SET:SYS:DR:ACTN:WARM')
        elif force:
            self.write('SET:SYS:DR:ACTN:WARM')

    def _parse_action(self, msg: str) -> str:
        """ Parse message and return action as a string
        Args:
            msg: message string
        Returns
            action: string describing the action
        """
        action = msg[17:]
        if action == 'PCL':
            action = 'Precooling'
        elif action == 'EPCL':
            action = 'Empty precool loop'
        elif action == 'COND':
            action = 'Condensing'
        elif action == 'NONE':
            if self.MC.get() < 2:
                action = 'Circulating'
            else:
                action = 'Idle'
        elif action == 'COLL':
            action = 'Collecting mixture'
        else:
            action = 'Unknown'
        return action

    def _parse_status(self, msg: str) -> str:
        return msg[19:]

    def _parse_time(self, msg: str) -> str:
        return msg[14:]

    def _parse_temp(self, msg: str) -> Optional[float]:
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:TEMP:')[-1].strip('K'))

    def _parse_pres(self, msg: str) -> Optional[float]:
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:PRES:')[-1].strip('mB')) * 1e3

    def _parse_state(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        state = msg.split(':')[-1].strip()
        return _parse_bool(state, 1, 0)

    def _parse_valve_state(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return msg.split(':')[-1].strip()

    def _parse_pump_speed(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:SPD:')[-1].strip('Hz'))

    def _parse_res(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split(':')[-1].strip('Ohm'))

    def _parse_swhtr(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        elif msg.split(' ')[-1].strip(']') == 'ON':
            return 1
        elif msg.split(' ')[-1].strip(']') == 'OFF':
            return 0
        else:
            print('unknown switch heater state')
            return msg

    def _parse_htr(self, msg):
        if 'NOT_FOUND' in msg:
            return None
        return float(msg.split('SIG:POWR:')[-1].strip('uW'))

    def _recv(self) -> str:
        return super()._recv().rstrip()

    def _checkquench(self):
        """Check wether the magnet is at field. Returns true if the magnet is
        close to 0"""
        if self.Bz() > 4e-5:
            print('The magnet is at field, I cannot proceed')
            return False
        else:
            return True


class IPS120(VisaInstrument):
    """
    Class to represent an Oxford Instruments IPS 120-10 superconducting magnet power supply
    """
    def __init__(self, name: str, address: str, **kwargs) -> None:
        """
        Args:
            name: Name to use internally in QCoDeS
            address: VISA resource address
        """
        super().__init__(name, address, terminator='\r', **kwargs)

        self.refresh_rate = 1

        self.field_setpoint = Parameter(
            "field_setpoint",
            unit="T",
            get_cmd=("R8"),
            set_cmd=("$J{:f}"),
            get_parser=self.__parse_return_float,
            vals=Numbers(min_value=-3, max_value=3),
            instrument=self
        )

        self.output_field = Parameter(
            "output_field",
            unit="T",
            get_cmd=("R7"),
            get_parser=self,
            instrument=self
        )

        self.switch_heater = Parameter(
            "switch_heater",
            get_cmd="X",
            get_parser=lambda s: self.__parse_examine_status(s, "H", 0),
            set_cmd="$H{:d}",
            vals=Bool(),
            #val_mapping={False: 0, True: 1, 2: 2, 5: 5, 8: 8},
            instrument=self
        )

        self.mode = Parameter(
            "mode",
            get_cmd="X",
            get_parser=lambda s: self.__parse_examine_status(s, "C", 0),
            set_cmd="$C{:d}",
            val_mapping={"local locked": 0, "remote locked": 1, "local": 2, "remote": 3},
            instrument=self
        )

        self.activity = Parameter(
            "activity",
            get_cmd="X",
            get_parser=lambda s: self.__parse_examine_status(s, "A", 0),
            set_cmd="$A{}",
            val_mapping={"hold": 0, "to set": 1, "to zero": 2, "clamped": 4},
            instrument=self
        )

        self.sweep_state = Parameter(
            "sweep_state",
            get_cmd="X",
            get_parser=lambda s: self.__parse_examine_status(s, "M", 1),
            val_mapping={"at rest": 0, "sweeping": 1, "sweep limiting": 2, "sweeping, sweep limiting": 3},
            instrument=self
        )

        self.field = IPSField(
            "field",
            instrument=self
        )

        self.connect_message()

    def __parse_return_float(self, return_value: str) -> float:
        return float(return_value.split("+")[-1])

    def __parse_examine_status(self, return_string: str, search_type: str, digit: int) -> int:
        matches = re.search("{}(\d+)".format(search_type), return_string)
        if matches:
            return int(matches.group(1)[digit])
        else:
            raise ValueError()

class IPSField(Parameter):
    """
    Class representing real field of the magnet implementing control logic
    """
    def __init__(self, name, instrument):
        super().__init__(name,
                         vals=Numbers(min_value=-3, max_value=3),
                         unit="T",
                         instrument=instrument
                         )

    def get_raw(self):
        return self.instrument.output_field()

    def set_raw(self, field):
        self.instrument.field_setpoint(field)
        self.instrument.activity("to set")
        sleep(self.instrument.refresh_rate)
        while "sweep" in self.instrument.sweep_state():
            sleep(self.instrument.refresh_rate)
        self.instrument.activity("hold")


def _parse_bool(value,
                on_val: Any = True,
                off_val: Any = False) -> Union[str, bool]:
    val_map = create_on_off_val_mapping(on_val, off_val)
    for key, val in val_map.items():
        if value == key:
            return val
        else:
            raise ValueError()


val_bool = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)
