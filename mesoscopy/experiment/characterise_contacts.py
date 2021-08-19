"""
functions to characterise contacts.
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
from typing import Optional

from station2004.triton.init_station import init_instruments
from qcodes import Measurement
from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.sqlite.queries import get_last_run
from qcodes.dataset.plotting import plot_dataset
from qcodes.utils.doNd import do0d, do1d


def _fit_iv(x, R, v):
    return R*x + v


def contact_IV(contact_number: str,
               measurement_name: str = "",
               exp: Optional[Experiment] = None,
               do_plot: Optional[bool] = None,
               do_fit: Optional[bool] = True):
    station = init_instruments()
    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_i(1e-7)
    station.keithley.smub.measurerange_v(0.2)
    station.keithey.smub.curr(1e-7)

    station.keithley.smub.fastsweep.prepareSweep(1e-7, -1e-7, 201, mode='VI')
    station.keithley.smub.output('on')

    do0d(station.keithley.smub.fastsweep,
         station.triton.T5,
         station.triton.T8,
         measurement_name='contact {contact_number}',
         exp=exp,
         do_plot=do_plot
         )
    station.keithley.smub.output('off')

    if do_fit:
        raw_data = get_last_run()
        meas = Measurement()
        meas.register_custom_parameter('current_fit',
                                       label='Current (fit)', unit='A',
                                       paramtype='array')
        meas.register_custom_parameter('voltage_fit',
                                       label='Voltage (fit)', unit='V',
                                       paramtype='array',
                                       setpoints=['current_fit'])
        meas.register_custom_parameter('fit_param_R',
                                       label='fitted parameter slope',
                                       unit='Ohm')
        meas.register_custom_parameter('fit_param_v',
                                       label='Fitted parameter offset',
                                       unit='V')
        meas.register_parent(parent=raw_data, link_type='curve fit')

        with meas.run() as datasaver:
            raw = datasaver.parent_datasets[0]
            xdata = np.ravel(raw.get_parameter_data()['signal']['time'])
            ydata = np.ravel(raw.get_parameter_data()['signal']['signal'])

            popt, pcov = opt.curve_fit(_fit_iv, xdata, ydata, p0=[100, 1e-9])

            fit_axis = xdata
            fit_curve = _fit_iv(fit_axis, *popt)

            datasaver.add_result(('fit_axis', fit_axis),
                                 ('fit_curve', fit_curve),
                                 ('fit_param_R', popt[0]),
                                 ('fit_param_v', popt[1]))
        fit_data = datasaver.dataset
        if do_plot:
            fig, ax = plt.subplots(1)
            cbs, axs = plot_dataset(raw_data, axes=ax, label='data')
            cbs, axs = plot_dataset(fit_data, axes=ax, label='fit', lw=1)
            ax.set_xlabel('')
            ax.set_ylabel('')
            plt.legend()


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

    do1d(station.keithley.smua.sweep)
