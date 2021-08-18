"""
functions to characterise contacts.
"""

import qcodes as qc
from typing import Optional
from station2004.triton.init_station import init_instruments


def contact_IV(contact_number: str):
    station = init_instruments()
    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_i(1e-7)
    station.keithley.smub.measurerange_v(0.2)
    station.keithey.smub.curr(1e-7)

    station.keithley.smub.fastsweep.prepareSweep(1e-7,-1e-7,201, mode='VI')
    station.keithley.smub.output('on')

    do0d(station.keithley.smub.fastsweep, station.triton.T5, station.triton.T8,
    do_plot  = True,
    measurement_name='contact {contact_number}')
    station.keithley.smub.output('off')


def contact_threeprobe(
    contact_number: str,
    range: Optional[float] = 20):

    station=init_instruments()
    station.keithley.smua.mode('voltage')
    station.keithley.smua.nplc(0.05)
    if range <= 20:
        station.keithley.smua.sourcerange_v(20)
    else:
        station.keithley.smua.sourcerange_v(200)
    station.keithley.smua.measurerange_i(1e-8)

    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_i(1e-8)
    station.keithley.smub.measurerange_v(0.2)
    station.keithley.smub.curr(1e-8)
    station.keithley.smub.output('on')

    station.keithley.smua.

    do1d(station.keithley.smua.sweep)
