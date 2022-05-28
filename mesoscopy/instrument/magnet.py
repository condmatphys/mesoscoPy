import configparser
import re
from functools import partial
import pyvisa
import logging
from traceback import format_exc
from typing import Optional, Any, Union, List, Dict
from numpy import array

from qcodes import IPInstrument, VisaInstrument
from qcodes.instrument.parameter import _BaseParameter
from qcodes.utils.validators import Enum, Ints, Numbers
from qcodes.utils.helpers import create_on_off_val_mapping

from time import sleep


# ---------------------------------
# functions to be used with magnets
# ---------------------------------


def calibrate_magnet(param_set: _BaseParameter,
                     mag_range: float = None,
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
    r"""
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

    def fullcooldown(self):
        '''Starts the full cooldown automation'''
        self.write('SET:SYS:DR:ACTN:CLDN')

    def condense(self):
        '''Starts condensing (use only if T < 12K)'''
        self.write('SET:SYS:DR:ACTN:COND')

    def mixture_collect(self):
        '''Starts collecting the mixture into the tank'''
        self.write('SET:SYS:DR:ACTN:COLL')

    def precool(self):
        '''Starts a pre-cool'''
        self.write('SET:SYS:DR:ACTN:PCL')

    def pause_precool(self):
        '''Pauses the pre-cool automation'''
        self.write('SET:SYS:DR:ACTN:PCOND')

    def resume_precool(self):
        '''Resumes the pre-cool automation'''
        self.write('SET:SYS:DR:ACTN:RCOND')

    def empty_precool(self):
        '''Starts the empty pre-cool circuit automation'''
        self.write('SET:SYS:DR:ACTN:EPCL')

    def stopcool(self):
        '''Stops any running automation'''
        self.write('SET:SYS:ACTN:STOP')

    def warmup(self):
        '''starts the system warm-up automation'''
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


def _parse_bool(value,
                on_val: Any = True,
                off_val: Any = False) -> Union[str, bool]:
    val_map = create_on_off_val_mapping(on_val, off_val)
    for key, val in val_map.items():
        if value == key:
            return val


val_bool = (0, 1, 'on', 'off', 'ON', 'OFF', False, True)

# following function from qcodes_contrib_drivers, under MIT license.
# adapted to resolve some bugs

log = logging.getLogger(__name__)

class OxfordInstruments_IPS120(VisaInstrument):
    """This is the driver for the Oxford Instruments IPS 120 Magnet Power Supply
    The IPS 120 can connect through both RS232 serial as well as GPIB. The
    commands sent in both cases are similar. When using the serial connection,
    commands are prefaced with '@n' where n is the ISOBUS number.
    """

    _GET_STATUS_MODE = {
            0: "Amps, Magnet sweep: fast",
            1: "Tesla, Magnet sweep: fast",
            4: "Amps, Magnet sweep: slow",
            5: "Tesla, Magnet sweep: slow",
            8 : "Amps, (Magnet sweep: unaffected)",
            9 : "Tesla, (Magnet sweep: unaffected)"}

    _GET_STATUS_MODE2 = {
            0: "At rest",
            1: "Sweeping",
            2: "Sweep limiting",
            3: "Sweeping & sweep limiting",
            5: "Unknown"}

    _GET_STATUS_SWITCH_HEATER = {
            0: "Off magnet at zero (switch closed)",
            1: "On (switch open)",
            2: "Off magnet at field (switch closed)",
            5: "Heater fault (heater is on but current is low)",
            8: "No switch fitted"}

    _GET_STATUS_REMOTE = {
            0: "Local and locked",
            1: "Remote and locked",
            2: "Local and unlocked",
            3: "Remote and unlocked",
            4: "Auto-run-down",
            5: "Auto-run-down",
            6: "Auto-run-down",
            7: "Auto-run-down"}

    _GET_SYSTEM_STATUS = {
            0: "Normal",
            1: "Quenched",
            2: "Over Heated",
            3: "Warming Up",
            4: "Fault"}

    _GET_SYSTEM_STATUS2 = {
            0: "Normal",
            1: "On positive voltage limit",
            2: "On negative voltage limit",
            3: "Outside negative current limit",
            4: "Outside positive current limit"}

    _GET_POLARITY_STATUS1 = {
            0: "Desired: Positive, Magnet: Positive, Commanded: Positive",
            1: "Desired: Positive, Magnet: Positive, Commanded: Negative",
            2: "Desired: Positive, Magnet: Negative, Commanded: Positive",
            3: "Desired: Positive, Magnet: Negative, Commanded: Negative",
            4: "Desired: Negative, Magnet: Positive, Commanded: Positive",
            5: "Desired: Negative, Magnet: Positive, Commanded: Negative",
            6: "Desired: Negative, Magnet: Negative, Commanded: Positive",
            7: "Desired: Negative, Magnet: Negative, Commanded: Negative"}

    _GET_POLARITY_STATUS2 = {
            1: "Negative contactor closed",
            2: "Positive contactor closed",
            3: "Both contactors open",
            4: "Both contactors closed"}

    _SET_ACTIVITY = {
            0: "Hold",
            1: "To set point",
            2: "To zero"}

    _WRITE_WAIT = 100e-3 # seconds

    def __init__(self, name, address, use_gpib=False, number=2, **kwargs):
        """Initializes the Oxford Instruments IPS 120 Magnet Power Supply.
        Args:
            name (str)    : name of the instrument
            address (str) : instrument address
            use_gpib (bool)  : whether to use GPIB or serial
            number (int)     : ISOBUS instrument number. Ignored if using GPIB.
        """
        super().__init__(name, address, terminator='\r', **kwargs)

        self._address = address
        self._number = number
        self._values = {}
        self._use_gpib = use_gpib

        # Add parameters
        self.add_parameter('mode',
                           get_cmd=self._get_mode,
                           set_cmd=self._set_mode,
                           vals=Ints())
        self.add_parameter('mode2',
                           get_cmd=self._get_mode2)
        self.add_parameter('activity',
                           get_cmd=self._get_activity,
                           set_cmd=self._set_activity,
                           vals=Ints())
        self.add_parameter('switch_heater',
                           get_cmd=self._get_switch_heater,
                           set_cmd=self._set_switch_heater,
                           vals=Ints())
        self.add_parameter('field_setpoint',
                           unit='T',
                           get_cmd=self._get_field_setpoint,
                           set_cmd=self._set_field_setpoint,
                           vals=Numbers(-14, 14))
        self.add_parameter('sweeprate_field',
                           unit='T/min',
                           get_cmd=self._get_sweeprate_field,
                           set_cmd=self._set_sweeprate_field,
                           vals=Numbers(0, 0.7))
        self.add_parameter('system_status',
                           get_cmd=self._get_system_status)
        self.add_parameter('system_status2',
                           get_cmd=self._get_system_status2)
        self.add_parameter('polarity',
                           get_cmd=self._get_polarity)
        self.add_parameter('voltage',
                           unit='V',
                           get_cmd=self._get_voltage)
        self.add_parameter('voltage_limit',
                           unit='V',
                           get_cmd=self._get_voltage_limit)

        # Find the F field limits
        MaxField = self.field_setpoint.vals._max_value
        MinField = self.field_setpoint.vals._min_value
        MaxFieldSweep = self.sweeprate_field.vals._max_value
        MinFieldSweep = self.sweeprate_field.vals._min_value
        # A to B conversion
        ABconversion = 115.733 / 14  # Ampere per Tesla
        self.add_parameter('current_setpoint',
                           unit='A',
                           get_cmd=self._get_current_setpoint,
                           set_cmd=self._set_current_setpoint,
                           vals=Numbers(ABconversion * MinField,
                                             ABconversion * MaxField))
        self.add_parameter('sweeprate_current',
                           unit='A/min',
                           get_cmd=self._get_sweeprate_current,
                           set_cmd=self._set_sweeprate_current,
                           vals=Numbers(ABconversion * MinFieldSweep,
                                             ABconversion * MaxFieldSweep))
        self.add_parameter('remote_status',
                           get_cmd=self._get_remote_status,
                           set_cmd=self._set_remote_status,
                           vals=Ints())
        self.add_parameter('current',
                           unit='A',
                           get_cmd=self._get_current)
        self.add_parameter('magnet_current',
                           unit='A',
                           get_cmd=self._get_magnet_current)
        self.add_parameter('field',
                           unit='T',
                           get_cmd=self._get_field)
        self.add_parameter('persistent_current',
                           unit='A',
                           get_cmd=self._get_persistent_current)
        self.add_parameter('persistent_field',
                           unit='T',
                           get_cmd=self._get_persistent_field)
        self.add_parameter('magnet_inductance',
                           unit='H',
                           get_cmd=self._get_magnet_inductance)
        self.add_parameter('lead_resistance',
                           unit='mOhm',
                           get_cmd=self._get_lead_resistance)
        self.add_parameter('current_limit_lower',
                           unit='A',
                           get_cmd=self._get_current_limit_lower)
        self.add_parameter('current_limit_upper',
                           unit='A',
                           get_cmd=self._get_current_limit_upper)
        self.add_parameter('heater_current',
                           unit='mA',
                           get_cmd=self._get_heater_current)
        self.add_parameter('trip_field',
                           unit='T',
                           get_cmd=self._get_trip_field)
        self.add_parameter('trip_current',
                           unit='A',
                           get_cmd=self._get_trip_current)

        if not self._use_gpib:
            self.visa_handle.set_visa_attribute(
                    visa.constants.VI_ATTR_ASRL_STOP_BITS,
                    visa.constants.VI_ASRL_STOP_TWO)
            # to handle VisaIOError which occurs at first read
            try:
                self.visa_handle.write('@%s%s' % (self._number, 'V'))
                sleep(self._WRITE_WAIT)
                self._read()
            except visa.VisaIOError:
                pass

    def get_all(self):
        """
        Reads all implemented parameters from the instrument,
        and updates the wrapper.
        """
        self.snapshot(update=True)

    def _execute(self, message):
        """
        Write a command to the device and return the result.
        Args:
            message (str) : write command for the device
        Returns:
            Response from the device as a string.
        """
        self.log.info('Send the following command to the device: %s' % message)

        if self._use_gpib:
            return self.ask(message)

        self.visa_handle.write('@%s%s' % (self._number, message))
        sleep(self._WRITE_WAIT)  # wait for the device to be able to respond
        result = self._read()
        if result.find('?') >= 0:
            print("Error: Command %s not recognized" % message)
        else:
            return result

    def _read(self):
        """
        Reads the total bytes in the buffer and outputs as a string.
        Returns:
            message (str)
        """
        bytes_in_buffer = self.visa_handle.bytes_in_buffer
        with(self.visa_handle.ignore_warning(visa.constants.VI_SUCCESS_MAX_CNT)):
            mes = self.visa_handle.visalib.read(
                self.visa_handle.session, bytes_in_buffer)
        mes = str(mes[0].decode())
        return mes

    def identify(self):
        """Identify the device"""
        self.log.info('Identify the device')
        return self._execute('V')

    def examine(self):
        """Examine the status of the device"""
        self.log.info('Examine status')

        print('System Status: ')
        print(self.system_status())

        print('Activity: ')
        print(self.activity())

        print('Local/Remote status: ')
        print(self.remote_status())

        print('Switch heater: ')
        print(self.switch_heater())

        print('Mode: ')
        print(self.mode())

        print('Polarity: ')
        print(self.polarity())

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
        self.log.info('Closing IPS120 connection')
        self.local()
        super().close()

    def get_idn(self):
        """
        Overides the function of Instrument since IPS120 does not support `*IDN?`
        This string is supposed to be a comma-separated list of vendor, model,
        serial, and firmware, but semicolon and colon are also common
        separators so we accept them here as well.
        Returns:
            A dict containing vendor, model, serial, and firmware.
        """
        idparts = ['Oxford Instruments', 'IPS120', None, None]

        return dict(zip(('vendor', 'model', 'serial', 'firmware'), idparts))

    def _get_remote_status(self):
        """
        Get remote control status
        Returns:
            result(str) :
            "Local & locked",
            "Remote & locked",
            "Local & unlocked",
            "Remote & unlocked",
            "Auto-run-down",
            "Auto-run-down",
            "Auto-run-down",
            "Auto-run-down"
        """
        self.log.info('Get remote control status')
        result = self._execute('X')
        return self._GET_STATUS_REMOTE[int(result[6])]

    def _set_remote_status(self, mode):
        """
        Set remote control status.
        Args:
            mode(int): Refer to _GET_STATUS_REMOTE for allowed values and
            meanings.
        """
        if mode in self._GET_STATUS_REMOTE.keys():
            self.log.info('Setting remote control status to %s'
                    % self._GET_STATUS_REMOTE[mode])
            self._execute('C%s' % mode)
        else:
            print('Invalid mode inserted: %s' % mode)

    def _get_system_status(self):
        """
        Get the system status
        Returns:
            result (str) :
            "Normal",
            "Quenched",
            "Over Heated",
            "Warming Up",
            "Fault"
        """
        result = self._execute('X')
        self.log.info('Getting system status')
        return self._GET_SYSTEM_STATUS[int(result[1])]

    def _get_system_status2(self):
        """
        Get the system status
        Returns:
            result (str) :
            "Normal",
            "On positive voltage limit",
            "On negative voltage limit",
            "Outside negative current limit",
            "Outside positive current limit"
        """
        result = self._execute('X')
        self.log.info('Getting system status')
        return self._GET_SYSTEM_STATUS2[int(result[2])]

    def _get_current(self):
        """
        Demand output current of device
        Returns:
            result (float) : output current in Amp
        """
        self.log.info('Read output current')
        result = self._execute('R0')
        return float(result.replace('R', ''))

    def _get_voltage(self):
        """
        Demand measured output voltage of device
        Returns:
            result (float) : output voltage in Volt
        """
        self.log.info('Read output voltage')
        result = self._execute('R1')
        return float(result.replace('R', ''))

    def _get_magnet_current(self):
        """
        Demand measured magnet current of device
        Returns:
            result (float) : measured magnet current in Amp
        """
        self.log.info('Read measured magnet current')
        result = self._execute('R2')
        return float(result.replace('R', ''))

    def _get_current_setpoint(self):
        """
        Return the set point (target current)
        Returns:
            result (float) : Target current in Amp
        """
        self.log.info('Read set point (target current)')
        result = self._execute('R5')
        return float(result.replace('R', ''))

    def _set_current_setpoint(self, current):
        """
        Set current setpoint (target current)
        Args:
            current (float) : target current in Amp
        """
        self.log.info('Setting target current to %s' % current)
        self.remote()
        self._execute('I%s' % current)
        self.local()
        self.field_setpoint()

    def _get_sweeprate_current(self):
        """
        Return sweep rate (current)
        Returns:
            result (float) : sweep rate in A/min
        """
        self.log.info('Read sweep rate (current)')
        result = self._execute('R6')
        return float(result.replace('R', ''))

    def _set_sweeprate_current(self, sweeprate):
        """
        Set sweep rate (current)
        Args:
            sweeprate(float) : Sweep rate in A/min.
        """
        self.remote()
        self.log.info('Set sweep rate (current) to %s A/min' % sweeprate)
        self._execute('S%s' % sweeprate)
        self.local()
        self.sweeprate_field()

    def _get_field(self):
        """
        Demand output field
        Returns:
            result (float) : magnetic field in Tesla
        """
        self.log.info('Read output field')
        result = self._execute('R7')
        return float(result.replace('R', ''))

    def _get_field_setpoint(self):
        """
        Return the set point (target field)
        Returns:
            result (float) : Field set point in Tesla
        """
        self.log.info('Read field set point')
        result = self._execute('R8')
        return float(result.replace('R', ''))

    def _set_field_setpoint(self, field):
        """
        Set the field set point (target field)
        Args:
            field (float) : target field in Tesla
        """
        self.log.info('Setting target field to %s' % field)
        self.remote()
        self._execute('J%s' % field)
        self.local()
        self.current_setpoint()

    def _get_sweeprate_field(self):
        """
        Return sweep rate (field)
        Returns:
            result (float) : sweep rate in Tesla/min
        """
        self.log.info('Read sweep rate (field)')
        result = self._execute('R9')
        return float(result.replace('R', ''))

    def _set_sweeprate_field(self, sweeprate):
        """
        Set sweep rate (field)
        Args:
            sweeprate(float) : Sweep rate in Tesla/min.
        """
        self.log.info('Set sweep rate (field) to %s Tesla/min' % sweeprate)
        self.remote()
        self._execute('T%s' % sweeprate)
        self.local()
        self.sweeprate_current()

    def _get_voltage_limit(self):
        """
        Return voltage limit
        Returns:
            result (float) : voltage limit in Volt
        """
        self.log.info('Read voltage limit')
        result = self._execute('R15')
        result = float(result.replace('R', ''))
        self.voltage.vals = vals.Numbers(-result, result)
        return result

    def _get_persistent_current(self):
        """
        Return persistent magnet current
        Returns:
            result (float) : persistent magnet current in Amp
        """
        self.log.info('Read persistent magnet current')
        result = self._execute('R16')
        return float(result.replace('R', ''))

    def _get_trip_current(self):
        """
        Return trip current
        Returns:
            result (float) : trip current om Amp
        """
        self.log.info('Read trip current')
        result = self._execute('R17')
        return float(result.replace('R', ''))

    def _get_persistent_field(self):
        """
        Return persistent magnet field
        Returns:
            result (float) : persistent magnet field in Tesla
        """
        self.log.info('Read persistent magnet field')
        result = self._execute('R18')
        return float(result.replace('R', ''))

    def _get_trip_field(self):
        """
        Return trip field
        Returns:
            result (float) : trip field in Tesla
        """
        self.log.info('Read trip field')
        result = self._execute('R19')
        return float(result.replace('R', ''))

    def _get_heater_current(self):
        """
        Return switch heater current
        Returns:
            result (float) : switch heater current in milliAmp
        """
        self.log.info('Read switch heater current')
        result = self._execute('R20')
        return float(result.replace('R', ''))

    def _get_current_limit_upper(self):
        """
        Return safe current limit, most positive
        Returns:
            result (float) : safe current limit, most positive in Amp
        """
        self.log.info('Read safe current limit, most positive')
        result = self._execute('R22')
        return float(result.replace('R', ''))

    def _get_current_limit_lower(self):
        """
        Return safe current limit, most negative
        Returns:
            result (float) : safe current limit, most negative in Amp
        """
        self.log.info('Read safe current limit, most negative')
        result = self._execute('R21')
        return float(result.replace('R', ''))

    def _get_lead_resistance(self):
        """
        Return lead resistance
        Returns:
            result (float) : lead resistance in milliOhm
        """
        self.log.info('Read lead resistance')
        result = self._execute('R23')
        return float(result.replace('R', ''))

    def _get_magnet_inductance(self):
        """
        Return magnet inductance
        Returns:
            result (float) : magnet inductance in Henry
        """
        self.log.info('Read magnet inductance')
        result = self._execute('R24')
        return float(result.replace('R', ''))

    def _get_activity(self):
        """
        Get the activity of the magnet. Possibilities: Hold, Set point, Zero or Clamp.
        Returns:
            result(str) : "Hold", "Set point", "Zero" or "Clamp".
        """
        self.log.info('Get activity of the magnet.')
        result = self._execute('X')
        return self._SET_ACTIVITY[int(result[4])]

    def _set_activity(self, mode):
        """
        Set the activity to Hold, To Set point or To Zero.
        Args:
            mode (int): See _SET_ACTIVITY for values and meanings.
        """
        if mode in self._SET_ACTIVITY.keys():
            self.log.info('Setting magnet activity to %s'
                    % self._SET_ACTIVITY[mode])
            self.remote()
            self._execute('A%s' % mode)
            self.local()
        else:
            print('Invalid mode inserted.')

    def hold(self):
        """Set the device activity to Hold"""
        self.activity(0)

    def to_setpoint(self):
        """Set the device activity to "To set point". This initiates a sweep."""
        self.activity(1)

    def to_zero(self):
        """
        Set the device activity to "To zero". This sweeps te magnet back to zero.
        """
        self.activity(2)

    def _get_switch_heater(self):
        """
        Get the switch heater status.
        Returns:
            result(str): See _GET_STATUS_SWITCH_HEATER.
        """
        self.log.info('Get switch heater status')
        result = self._execute('X')
        return self._GET_STATUS_SWITCH_HEATER[int(result[8])]

    def _set_switch_heater(self, mode):
        """
        Set the switch heater Off or On. Note: After issuing a command it is necessary to wait
        several seconds for the switch to respond.
        Args:
            mode (int) :
            0 : Off
            1 : On
        """
        if mode in [0, 1]:
            self.log.info('Setting switch heater to %d' % mode)
            self.remote()
            self._execute('H%s' % mode)
            print("Setting switch heater... (wait 40s)")
            self.local()
            sleep(40)
        else:
            print('Invalid mode inserted.')
        sleep(0.1)
        self.switch_heater()

    def heater_on(self):
        """Switch the heater on, with PSU = Magnet current check"""
        current_in_magnet = self.persistent_current()
        current_in_leads = self.current()
        if self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[1]:
            print('Heater is already on!')
        else:
            if self.mode2() == self._GET_STATUS_MODE2[0]:
                if current_in_leads == current_in_magnet:
                    self.switch_heater(1)
                else:
                    print('Current in the leads is not matching persistent current!')
            else:
                print('Magnet supply not at rest, cannot switch on heater!')
        self.switch_heater()

    def set_persistent(self):
        """
        Puts magnet into persistent mode
        Note: After turning of the switch heater we will wait for additional 20
        seconds before we put the current to zero. This is done to make sure
        that the switch heater is cold enough and becomes superconducting.
        """
        if self.mode2() == self._GET_STATUS_MODE2[0]:
            self.heater_off()
            print('Waiting for the switch heater to become superconducting')
            sleep(20)
            self.to_zero()
            self.get_all()
        else:
            print('Magnet is not at rest, cannot put it in persistent mode')
        self.get_all()

    def leave_persistent_mode(self):
        """
        Read out persistent current, match the current in the leads to that current
        and switch on heater
        """
        if self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[2]:
            field_in_magnet = self.persistent_field()
            field_in_leads = self.field()
            self.hold()
            self.field_setpoint(field_in_magnet)
            self.to_setpoint()

            while field_in_leads != field_in_magnet:
                field_in_leads = self.field()
            self.heater_on()
            self.hold()

        elif self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[1]:
            print('Heater is already on, so the magnet was not in persistent mode')
        elif self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[0]:
            print('Heater is off, field is zero. Turning on switch heater.')
            self.heater_on()

        self.get_all()

    def run_to_field(self, field_value):
        """
        Go to field value
        Args:
            field_value (float): the magnetic field value to go to in Tesla
        """

        if self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[1]:
            self.hold()
            self.field_setpoint(field_value)
            self.to_setpoint()
        else:
            print('Switch heater is off, cannot change the field.')
        self.get_all()

    def run_to_field_wait(self, field_value):
        """
        Go to field value and wait until it's done sweeping.
        Args:
            field_value (float): the magnetic field value to go to in Tesla
        """
        if self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[1]:
            self.hold()
            self.field_setpoint(field_value)
            self.remote()
            self.to_setpoint()
            magnet_mode = self.mode2()
            while magnet_mode != self._GET_STATUS_MODE2[0]:
                magnet_mode = self.mode2()
                sleep(0.5)
        else:
            print('Switch heater is off, cannot change the field.')
        self.get_all()
        self.local()

    def heater_off(self):
        """Switch the heater off"""
        if (self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[0] or
                self.switch_heater() == self._GET_STATUS_SWITCH_HEATER[2]):
            print('Heater is already off!')
        else:
            if self.mode2() == self._GET_STATUS_MODE2[0]:
                self.switch_heater(0)
            else:
                print('Magnet is not at rest, cannot switch of the heater!')

    def _get_mode(self):
        """
        Get the mode of the device
        Returns:
            mode(str): See _GET_STATUS_MODE.
        """
        self.log.info('Get device mode')
        result = self._execute('X')
        return self._GET_STATUS_MODE[int(result[10])]

    def _get_mode2(self):
        """
        Get the sweeping mode of the device
        Returns:
            mode(str): See _GET_STATUS_MODE2.
        """
        self.log.info('Get device mode')
        result = self._execute('X')
        return self._GET_STATUS_MODE2[int(result[11])]

    def _set_mode(self, mode):
        """
        Args:
            mode(int): Refer to _GET_STATUS_MODE dictionary for the allowed
            mode values and meanings.
        """
        if mode in self._GET_STATUS_MODE.keys():
            self.log.info('Setting device mode to %s' % self._GET_STATUS_MODE[mode])
            self.remote()
            self._execute('M%s' % mode)
            self.local()
        else:
            print('Invalid mode inserted.')

    def _get_polarity(self):
        """
        Get the polarity of the output current
        Returns:
            result (str): See _GET_POLARITY_STATUS1 and _GET_POLARITY_STATUS2.
        """
        self.log.info('Get device polarity')
        result = self._execute('X')
        return self._GET_POLARITY_STATUS1[int(result[13])] + \
            ", " + self._GET_POLARITY_STATUS2[int(result[14])]
