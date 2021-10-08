"""
functions to characterise contacts.
works with a Keithley 2600 and Oxford Triton
beware using twoprobe_contacts - may burn device. function still under test
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
from typing import Optional

from qcodes import Measurement, Station, ScaledParameter
from qcodes.dataset.experiment_container import Experiment
from qcodes.instrument.parameter import _BaseParameter
from qcodes.dataset.plotting import plot_dataset
from qcodes.utils.dataset.doNd import do0d

from ..measurement.array import generate_1D_sweep_array
from ..measurement.sweep import sweep1d, fastsweep
from ..measurement._utils import _threshold


def _fit_iv(x, R, v):
    return R*x + v


def contact_IV(contact_number: int,
               station: Station,
               *meas_param: _BaseParameter,
               exp: Optional[Experiment] = None,
               do_plot: Optional[bool] = None,
               do_fit: Optional[bool] = True,
               ):
    # TODO: make this function work with different instruments: either
    # keithley 2400/2450 or 2600.

    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_i(1e-7)
    station.keithley.smub.measurerange_v(0.2)
    station.keithley.smub.curr(1e-7)

    station.keithley.smub.fastsweep.prepareSweep(1e-7, -1e-7, 201, mode='VI')
    station.keithley.smub.output('on')

    raw_data = do0d(station.keithley.smub.fastsweep,
                    *meas_param,
                    measurement_name=f'contact {contact_number}',
                    exp=exp,
                    do_plot=do_plot and not do_fit
                    )
    station.keithley.smub.output('off')

    if do_fit:
        meas = Measurement(name=f'fit contact {contact_number}')
        meas.register_custom_parameter('fit_curr', label='Current', unit='A',
                                       paramtype='array')
        meas.register_custom_parameter('fit_volt',
                                       label='Voltage', unit='V',
                                       paramtype='array',
                                       setpoints=['fit_curr'])
        meas.register_custom_parameter('fit_R',
                                       label='fitted resistance',
                                       unit='Ohm')
        meas.register_custom_parameter('fit_v',
                                       label='Fitted voltage offset',
                                       unit='V')
        meas.register_parent(parent=raw_data[0], link_type='curve fit')

        with meas.run() as datasaver:
            raw = datasaver.parent_datasets[0]
            xdata = np.ravel(raw.get_parameter_data(
            )['keithley_smub_vi_sweep']['keithley_smub_Current'])
            ydata = np.ravel(raw.get_parameter_data(
            )['keithley_smub_vi_sweep']['keithley_smub_vi_sweep'])

            popt, pcov = opt.curve_fit(_fit_iv, xdata, ydata, p0=[100, 1e-9])

            fit_curr = xdata
            fit_volt = _fit_iv(fit_curr, *popt)

            datasaver.add_result(('fit_curr', fit_curr),
                                 ('fit_volt', fit_volt),
                                 ('fit_R', popt[0]),
                                 ('fit_v', popt[1]))
        fit_data = datasaver.dataset
        if do_plot:
            fig, ax = plt.subplots(1)
            cbs, axs = plot_dataset(raw_data[0], axes=ax, label='data', c='C0')
            cbs, axs = plot_dataset(fit_data, axes=ax,
                                    label='fit', lw=1, c='C1')
            leg0 = plt.legend(loc=2)
            leg1 = plt.legend([], [''], loc=4,
                              title='R = {}kΩ\n'
                              'y = {:.2e} * x + {:.2e}'
                              .format(round(popt[0]/1e3), popt[0], popt[1]))
            ax.add_artist(leg0)
            ax.add_artist(leg1)


def twoprobe_contacts(
    contact_number: int,
    station: Station,
    *meas_param: _BaseParameter,
    exp: Optional[Experiment] = None,
    sweeprange: Optional[float] = 20,
    do_plot: Optional[bool] = None,
):

    station.keithley.smua.mode('voltage')
    station.keithley.smua.nplc(0.05)
    if sweeprange <= 20:
        station.keithley.smua.sourcerange_v(20)
        station.keithley.smua.limitv(20)
    else:
        station.keithley.smua.sourcerange_v(200)
        station.keithley.smua.limitv(80)
    station.keithley.smua.measurerange_i(1e-7)
    station.keithley.smua.limiti(1e-9)  # add safety
    station.keithley.smua.output('on')

    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.limitv(.02)  # add safety
    station.keithley.smub.limiti(1e-8)  # add safety
    station.keithley.smub.sourcerange_i(1e-7)
    station.keithley.smub.measurerange_v(0.2)
    station.keithley.smub.curr(1e-8)
    station.keithley.smub.output('on')

    Rc = ScaledParameter(station.keithley.smub.volt,
                         division=1e-8,
                         unit='Ω',
                         label='contact resistance',
                         name='contact_resistance')

    vmax = fastsweep(sweeprange, station.keithley.smua.volt,
                     control=_threshold(station.keithley.smua.curr),
                     lbar=True)

    array = generate_1D_sweep_array(vmax, -vmax, num=201)

    raw_data = sweep1d(station.keithley.smua.volt,
                       array,
                       .05,  # delay between points in sec
                       Rc,
                       station.keithley.smub.volt,
                       station.keithley.smub.curr,
                       station.keitley.smua.curr,
                       *meas_param,
                       exp=exp,
                       measurement_name=f'contact {contact_number}'
                                        'gate dependence',
                       use_threads=True,
                       )
    fastsweep(0, station.keithley.smua.volt,
              lbar=True)

    if do_plot:
        fig, [ax, ax1] = plt.subplots(2)
        cbs, axs = plot_dataset(raw_data, axes=[ax, ax1, ax1, ax1, ax1])
        ax1.set_visible(False)

    return raw_data


def test_gate(label: str,
              station: Station,
              *meas_param: _BaseParameter,
              exp: Optional[Experiment] = None,
              sweeprange: Optional[float] = 20,
              do_plot: Optional[bool] = None,
              ):

    if station.triton.T5() > 70:
        print('device temperature is {}K. It is not safe to test the gate.'
              'ABORT.'.format(station.triton.T5()))
        return

    station.keithley.smua.mode('voltage')
    station.keithley.smua.nplc(0.05)

    if sweeprange <= 20:
        station.keithley.smua.sourcerange_v(20)
        station.keithley.smua.limitv(20)
    else:
        station.keithley.smua.sourcerange_v(200)
        station.keithley.smua.limitv(80)
    station.keithley.smua.measurerange_i(1e-7)

    vmax = fastsweep(sweeprange, station.keithley.smua.volt,
                     control=_threshold(station.keithley.smua.curr),
                     lbar=True,)
    if vmax < 2:
        print(f'{label} not working')
        fastsweep(sweeprange, station.keithley.smua.volt,
                  lbar=True,)
        return
    else:
        print(f'{label} working up to {vmax} V')

    array = generate_1D_sweep_array(vmax, -vmax, num=201)
    dataset = sweep1d(station.keithley.smua.volt,
                      array,
                      0.05,
                      station.keithley.smua.curr,
                      *meas_param,
                      exp=exp,
                      measurement_name=f'test gate {label}',
                      use_threads=True)

    fastsweep(0, station.keithley.smua.volt, lbar=True)

    if do_plot:
        fig, [ax, ax1] = plt.subplots(2)
        cbs, axs = plot_dataset(dataset, axes=[ax, ax1])
        ax1.set_visible(False)
    return dataset
