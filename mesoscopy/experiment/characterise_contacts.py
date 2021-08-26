"""
functions to characterise contacts.
works with a Keithley 2600 and Oxford Triton
beware using twoprobe_contacts - may burn device. function still under test
"""

import time
import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
from typing import Optional
from tqdm.auto import tqdm

from qcodes import Measurement, Station, ScaledParameter
from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.plotting import plot_dataset
from qcodes.utils.dataset.doNd import do0d

from ..instrument.instrument_tools import create_instrument, add_to_station
from ..measurement.array import generate_1D_sweep_array
from ..measurement.sweep import sweep1d


def _fit_iv(x, R, v):
    return R*x + v


def _go_to(v0, v1,
           station: Station,
           desc: Optional[str] = None,
           threshold: Optional[float] = None,
           ):
    array = generate_1D_sweep_array(v0, v1, step=2e-1)
    time.sleep(.5)
    for v in tqdm(array, leave=False, desc=desc):
        station.keithley.smua.volt(v)
        time.sleep(0.05)
        if threshold and station.keithley.smua.curr() > threshold:
            break
    time.sleep(.5)
    return v


def station_contacts_triton(
    keithley_addr: str,
    triton_addr: str
):
    """ function to initialise the station for contact measurement """
    station = Station()
    from qcodes.instrument_drivers.tektronix.Keithley_2600_channels import \
        Keithley_2600
    keithley = create_instrument(Keithley_2600, "keithley",
                                 address=keithley_addr,
                                 force_new_instance=True)
    add_to_station(keithley, station)
    from qcodes.instrument_drivers.oxford.triton import Triton
    triton = create_instrument(Triton, "triton", address=triton_addr,
                               port=33576, force_new_instance=True)
    add_to_station(triton, station)

    return station


def contact_IV(contact_number: int,
               station: Station,
               T_channel: Optional[str] = "T8",
               exp: Optional[Experiment] = None,
               do_plot: Optional[bool] = None,
               do_fit: Optional[bool] = True,
               ):
    """
    TODO:
        make this function independent of temperature channel instrument
        with t_channel being an Instrument.Parameter
    """
    station.keithley.smub.mode('current')
    station.keithley.smub.nplc(0.05)
    station.keithley.smub.sourcerange_i(1e-7)
    station.keithley.smub.measurerange_v(0.2)
    station.keithley.smub.curr(1e-7)

    station.keithley.smub.fastsweep.prepareSweep(1e-7, -1e-7, 201, mode='VI')
    station.keithley.smub.output('on')

    raw_data = do0d(station.keithley.smub.fastsweep,
                    station.triton[T_channel],
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
    exp: Optional[Experiment] = None,
    sweeprange: Optional[float] = 20,
    do_plot: Optional[bool] = None,
    T_channel: Optional[str] = 'T8'
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

    init = station.keithley.smua.volt()
    vmax = _go_to(init, sweeprange, station,
                  desc=f'sweeping to {sweeprange}V',
                  threshold=1e-9)

    array = generate_1D_sweep_array(vmax, -vmax, num=201)

    raw_data = sweep1d(station.keithley.smua.volt,
                       array,
                       .05,  # delay between points in sec. <- maybe error
                       Rc,
                       station.keithley.smub.volt,
                       station.keithley.smub.curr,
                       station.keitley.smua.curr,
                       station.triton[T_channel],
                       exp=exp,
                       measurement_name=f'contact {contact_number}'
                                        'gate dependence',
                       use_threads=True,
                       )
    _go_to(-vmax, 0, station, desc='sweeping back to 0')

    if do_plot:
        fig, [ax, ax1] = plt.subplots(2)
        cbs, axs = plot_dataset(raw_data, axes=[ax, ax1, ax1, ax1, ax1])
        ax1.set_visible(False)
        ax.legend([], [], title='{} K'.format(
            round(station.triton[T_channel](), 2)))

    return raw_data


def test_gate(label: str,
              station: Station,
              exp: Optional[Experiment] = None,
              sweeprange: Optional[float] = 20,
              do_plot: Optional[bool] = None,
              T_channel: Optional[str] = 'T8',
              ):

    if station.triton[T_channel]() > 70:
        print('device temperature is {}K. It is not safe to test the gate.'
              'ABORT.'.format(station.triton[T_channel]()))
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

    meas = Measurement(exp=exp, name=f'test gate {label}')
    meas.register_parameter(station.keithley.smua.volt)
    meas.register_parameter(station.keithley.smua.curr,
                            setpoints=(station.keithley.smua.volt,))
    meas.register_parameter(station.triton[T_channel],
                            setpoints=(station.keithley.smua.volt,))

    init = station.keithley.smua.volt()

    vmax = _go_to(init, sweeprange,
                  station,
                  desc=f'sweeping to {sweeprange} V',
                  threshold=1e-9)
    if vmax < 2:
        print(f'{label} not working')
        _go_to(vmax, 0, station, desc='sweeping back to 0')
        return
    else:
        print(f'{label} working up to {vmax} V')

    array = generate_1D_sweep_array(vmax, -vmax, num=201)

    with meas.run() as datasaver:
        for v in tqdm(array):
            station.keithley.smua.volt.set(v)
            vali = station.keithley.smua.curr.get()
            T = station.triton[T_channel]()
            datasaver.add_result((station.keithley.smua.volt, v),
                                 (station.keithley.smua.curr, vali),
                                 (station.triton[T_channel], T)
                                 )
            time.sleep(0.05)
    _go_to(-vmax, 0, station, desc='sweeping back to 0')
    dataset = datasaver.dataset

    if do_plot:
        fig, [ax, ax1] = plt.subplots(2)
        cbs, axs = plot_dataset(dataset, axes=[ax, ax1])
        ax1.set_visible(False)
        ax.legend([], [], title='{} K'.format(
            round(station.triton[T_channel](), 2)))
    return dataset


if __name__ == 'main__':
    station = station_contacts_triton()
