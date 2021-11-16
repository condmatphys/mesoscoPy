"""
tools to facilitate setting up an experimental station with instruments
some functions are based on pytopo (https://github.com/kouwenhovenlab/pytopo)
"""

from typing import Tuple
from scipy.constants import e, epsilon_0
import qcodes as qc
from qcodes.instrument.parameter import _BaseParameter, Parameter


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
            qc.Instrument._all_instruments[name]().close()
            return self(name, *arg, **kwarg)

        return qc.Instrument._all_instruments[name]()


def disconnect_instrument(name):
    """
    force disconnect an instrument
    """
    qc.Instrument._all_instruments[name]().close()


def add_to_station(instrument, station):
    """
    add instrument <instrument> to station <station>.
    """

    if instrument.name in station.components:
        del station.components[instrument.name]

    station.add_component(instrument)
    return station
