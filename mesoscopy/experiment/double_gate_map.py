"""
functions to make a double gate map
works with Keithley 2600, Oxford Triton and Zurich Instrument
MFLI lock-in amplifiers
"""

from typing import Optional

from qcodes import Station, Instrument
from qcodes.dataset.experiment_container import Experiment

import zhinst.qcodes

from ..instrument.smu import init_smu
from ..measurement.sweep import sweep2d, fastsweep


def gate_map(
    xarray,
    inner_delay,
    yarray, outer_delay,
    station: Station,
    exp: Optional[Experiment] = None,
    label: Optional[str] = None,
    measure_retrace: Optional[bool] = False,
):

    init_smu(station)
    # NOTE: this does not take into account any change in the compliance limit.
    # limits that were previously set up will be overwritten at that point.
    # TODO: make the function useable with different kinds of keithleys

    lockins = []
    for name, itm in station.components.items():
        if isinstance(itm, Instrument):
            if itm.__class__ == zhinst.qcodes.mfli.MFLI:
                lockins.append(name)

    fastsweep(xarray[0], station.keithley.smua.volt, lbar=True)
    fastsweep(yarray[0], station.keithley.smub.volt, lbar=True)

    raw_data = sweep2d(
        station.keithley.smua.volt,
        xarray,
        inner_delay,
        station.keithley.smub.volt,
        yarray,
        outer_delay,
        *tuple(station.__getattr__(lockin).demods[0].sample
               for lockin in lockins),
        station.triton.T8,
        station.triton.Bz,
        station.keithley.smua.curr,
        station.keithley.smub.curr,
        exp=exp,
        measurement_name=f'gate map {label}',
        use_threads=True,
        measure_retrace=measure_retrace,
    )

    return raw_data
