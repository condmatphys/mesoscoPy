import logging
from qcodes import VisaInstrument
from qcodes.utils.validators import Ints, Enum, Numbers
from qcodes.utils.helpers import create_on_off_val_mapping
import pyvisa


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
        Overrides the function of Insrtument since ITC503 does not support `*IDN?`
        Returns:
            dict containing vendor, model, serial, firmware
        """
        idparts = ['Oxford Instruments', 'ITC503', None, None]
        return dict(zip(('vendor', 'model', 'serial', 'firmware'),idparts))

    def _execute(self, message):
        """ write a command to the device, return the result
        Args:
            message (str): command for the device
        """
        self.log.info('Send the following command to the device: %s' %message)
        if self._use_gpib:
            return self.ask(message)

        self.visa_handle.write('@%s%s' %(self._number, message))
        sleep(self._WRITE_WAIT)
        result = self._read()
        if result.find('?') >= 0:
            print('Error: Command %s not recognised' %message)
        else:
            return result

    def _get_mode(self):
        """get the mode of the device.
        Returns:
            mode(str): see _GET_STATUS_MODE.
        """
        self.log.info('Get device mode')
        result = self._execute('X')
        return self._GET_STATUS_MODE[int(result[10])]

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
