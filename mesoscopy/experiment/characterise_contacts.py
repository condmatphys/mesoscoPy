"""
functions to characterise contacts.
works with a Keithley 2600 and Oxford Triton
"""

import numpy as np
import matplotlib.pyplot as plt
import scipy.optimize as opt
from typing import Optional, Union
from pathlib import Path

from qcodes import Measurement, Station
from qcodes.dataset.experiment_container import Experiment
from qcodes.dataset.plotting import plot_dataset
from qcodes.utils.dataset.doNd import do0d, do1d

from ..instrument.instrument_tools import create_instrument, add_to_station


def _fit_iv(x, R, v):
    return R*x + v


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


def contact_IV(contact_number: str,
               station: Station,
               measurement_name: str = "",
               T_channel: Optional[str] = "T8",
               exp: Optional[Experiment] = None,
               do_plot: Optional[bool] = None,
               do_fit: Optional[bool] = True,
               db_path: Optional[Union[str, Path]] = None):
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
                    do_plot=False
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
            ydata = np.ravel(raw.get_prameter_data(
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
                              title='R = {}kΩ'
                              'y = {:.2e} * x + {:.2e}'
                              .format(round(popt[0]/1e3), popt[0], popt[1]))
            ax.add_artist(leg0)
            ax.add_artist(leg1)


def contact_threeprobe(
    contact_number: str,
    range: Optional[float] = 20
):

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


if __name__ == 'main__':
    station = station_contacts_triton()
