from qcodes import VisaInstrument
from qcodes import validators
import pyvisa


# -----------------------------
# temperature controler drivers
# -----------------------------

class OxfordInstruments_ITC503(VisaInstrument):
    """
    This is the driver for the Oxford Insruments ITC 50 Temperature Controller

    The ITC503 can connect through both RS232 serial as well as GPIB.
    The commands sent in both cases are similar. When using the serial connection,
    commands are prefaced with '@n' where n is the ISOBUS number.
    """

    _GET_STATUS_REMOTE = {
        0: 'Local and locked',
        1: 'Remote and locked',
        2: 'Local and unlocked',
        3: 'Remote and unlocked'
    }

    _GET_STATUS_MODE = {
        0: 'Hold',
        1: 'Sweep'
    }


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
                           vals=validators.Ints())
                           
