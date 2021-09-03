"""
calculate time for sweep functions
"""

from datetime import datetime, timedelta
from typing import (Optional, Sequence, Callable)
from warnings import simplefilter
from qcodes.dataset.experiment_container import Experiment
from qcodes.utils.dataset import doNd
from qcodes.instrument.parameter import _BaseParameter
from .array import generate_1D_sweep_array


def _safesweep_time(target, param: _BaseParameter):
    init = param.get()
    if 'max_rate' in param._instrument.__dict__ and \
            param._instrument.max_rate() > 0.:
        step = param._instrument.max_rate()/100
        simplefilter('ignore')
        array = generate_1D_sweep_array(init, target, step=step)
    else:
        array = [target]
    t = 0.01*len(array) + .0001
    return t


def fastsweep_time(target,
                   param: _BaseParameter,
                   step: Optional[float] = .1,
                   actions: doNd.ActionsT = (),
                   control: Optional[Callable] = None,
                   lbar: Optional[bool] = False):
    init = param.get()
    simplefilter('ignore')
    array = generate_1D_sweep_array(init, target, step=step)
    t = .05 + (_safesweep_time(step, param) + 0.01)*len(array)

    finish = datetime.now() + timedelta(seconds=t)
    print(f'fastsweep will finish on {finish}')
    return t


def sweep1d_time(param_set: _BaseParameter,
                 xarray,
                 delay: float,
                 *param_meas: doNd.ParamMeasT,
                 exp: Optional[Experiment] = None,
                 measurement_name: Optional[str] = None,
                 use_threads: Optional[bool] = None,
                 enter_actions: doNd.ActionsT = (),
                 exit_actions: doNd.ActionsT = (),
                 additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
                 ):
    t = _safesweep_time(xarray[0], param_set)
    t += abs(_safesweep_time(xarray[1], param_set) -
             _safesweep_time(xarray[0], param_set) + delay) * len(xarray)

    finish = datetime.now() + timedelta(seconds=t)
    print(f'1d sweep will finish on {finish}')
    return t


def sweep1d_repeat(param_set: _BaseParameter,
                   xarray,
                   inner_delay: float,
                   *param_meas: doNd.ParamMeasT,
                   num_repeat: int = 1,
                   outer_delay: float = .1,
                   exp: Optional[Experiment] = None,
                   measurement_name: Optional[str] = None,
                   use_threads: Optional[bool] = None,
                   outer_enter_actions: doNd.ActionsT = (),
                   outer_exit_actions: doNd.ActionsT = (),
                   inner_enter_actions: doNd.ActionsT = (),
                   inner_exit_actions: doNd.ActionsT = (),
                   measure_retrace: Optional[bool] = False,
                   num_retrace: Optional[str] = 201,
                   additional_setpoints: Sequence[doNd.ParamMeasT] = tuple()
                   ):

    t = abs(_safesweep_time(xarray[1], param_set) -
            _safesweep_time(xarray[0], param_set) + inner_delay)*len(xarray)
    if not measure_retrace:
        t += abs(_safesweep_time(xarray[-1], param_set) -
                 _safesweep_time(xarray[0], param_set))
    t *= num_repeat
    t += _safesweep_time(xarray[0], param_set)  # time to sweep to the first
    # point. added at the end because of multiplication

    finish = datetime.now() + timedelta(seconds=t)
    print(f'1d_repeat will finish on {finish}')
    return t


def sweep2d_time(param_setx: _BaseParameter,
                 xarray,
                 inner_delay: float,
                 param_sety: _BaseParameter,
                 yarray,
                 outer_delay: float = .1,
                 *param_meas: doNd.ParamMeasT,
                 exp: Optional[Experiment] = None,
                 measurement_name: Optional[str] = None,
                 use_threads: Optional[bool] = None,
                 outer_enter_actions: doNd.ActionsT = (),
                 outer_exit_actions: doNd.ActionsT = (),
                 inner_enter_actions: doNd.ActionsT = (),
                 inner_exit_actions: doNd.ActionsT = (),
                 measure_retrace: Optional[bool] = False,
                 num_retrace: Optional[str] = 201,
                 additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
                 ):
    t = abs(_safesweep_time(xarray[1], param_setx) -
            _safesweep_time(xarray[0], param_setx) + inner_delay) * len(xarray)
    if not measure_retrace:
        t += abs(_safesweep_time(xarray[-1], param_setx) -
                 _safesweep_time(xarray[0], param_setx))
    t += abs(_safesweep_time(yarray[1], param_sety) -
             _safesweep_time(yarray[0], param_sety))
    t *= len(yarray)
    t += _safesweep_time(yarray[0], param_sety)
    t += _safesweep_time(xarray[0], param_setx)  # time to sweep to the first
    # point. added at the end because of multiplication

    finish = datetime.now() + timedelta(seconds=t)
    print(f'2d sweep will finish on {finish}')
    return t
