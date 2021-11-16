"""
sweep functions
"""

import time
from typing import (Optional, Sequence, Callable)
from warnings import warn
from tqdm.auto import tqdm

from qcodes.dataset.measurements import Measurement
from qcodes.dataset.experiment_container import Experiment
from qcodes.instrument.parameter import _BaseParameter
from qcodes.dataset.descriptions.detect_shapes import \
    detect_shape_of_measurement
from qcodes.utils.dataset import doNd
from qcodes.dataset.descriptions.versioning.rundescribertypes import Shapes

from ._utils import _is_monotonic, _safesweep_to
from .parameters import CountParameter, TimeParameter
from .array import generate_1D_sweep_array


def fastsweep(target,
              param: _BaseParameter,
              step: Optional[float] = .1,
              actions: doNd.ActionsT = (),
              control: Optional[Callable] = None,
              lbar: Optional[bool] = False):
    init = param.get()
    array = generate_1D_sweep_array(init, target, step=step)
    time.sleep(.05)
    if lbar:
        array = tqdm(array, leave=False)
    for v in array:
        _safesweep_to(v, param)
        time.sleep(0.01)
        for action in actions:
            action()
        if control:
            break
    return v


def sweep1d(param_set: _BaseParameter,
            xarray,
            delay: float,
            *param_meas: doNd.ParamMeasT,
            exp: Optional[Experiment] = None,
            measurement_name: Optional[str] = None,
            do_plot: Optional[bool] = None,
            use_threads: Optional[bool] = None,
            enter_actions: doNd.ActionsT = (),
            exit_actions: doNd.ActionsT = (),
            additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
            ):

    if not _is_monotonic(xarray):
        warn('The array over which sweep is being made is not monotonic.')

    meas = Measurement(exp=exp, name=measurement_name)

    all_setpoint_params = (param_set,) + tuple(
        s for s in additional_setpoints)

    measured_parameters = tuple(param for param in param_meas
                                if isinstance(param, _BaseParameter))

    if not use_threads:
        use_threads = False
    elif len(measured_parameters) > 2 or use_threads:
        use_threads = True
    else:
        use_threads = False

    try:
        loop_shape = tuple(1 for _ in additional_setpoints) + (len(xarray),)
        shapes: Shapes = detect_shape_of_measurement(
            measured_parameters,
            loop_shape
        )
    except TypeError:
        warn(f" shape of {measured_parameters} unknown ")
        shapes = None

    doNd._register_parameters(meas, all_setpoint_params)
    doNd._register_parameters(meas, param_meas, setpoints=all_setpoint_params,
                              shapes=shapes)
    doNd._register_actions(meas, enter_actions, exit_actions)

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasaver:

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)
        for set_point in tqdm(xarray):
            _safesweep_to(set_point, param_set)
            time.sleep(delay)
            datasaver.add_result(
                (param_set, set_point),
                *doNd.process_params_meas(param_meas,
                                          use_threads=use_threads),
                *additional_setpoints_data
            )
        dataset = datasaver.dataset

    return doNd._handle_plotting(dataset, do_plot, interrupted())


def sweeptime(timeout: float,
              delay: float,
              *param_meas: doNd.ParamMeasT,
              exp: Optional[Experiment] = None,
              measurement_name: Optional[str] = None,
              do_plot: Optional[bool] = None,
              use_threads: Optional[bool] = False,
              enter_actions: doNd.ActionsT = (),
              exit_actions: doNd.ActionsT = (),
              additional_setpoints=tuple()):

    meas = Measurement(exp=exp, name=measurement_name)
    timer = TimeParameter("time")

    all_setpoint_params = (timer,) + tuple(
        s for s in additional_setpoints)

    measured_parameters = list(param for param in param_meas
                               if isinstance(param, _BaseParameter))

    if not use_threads:
        use_threads = False
    elif len(measured_parameters) > 2 or use_threads:
        use_threads = True
    else:
        use_threads = False

    doNd._register_parameters(meas, all_setpoint_params)
    doNd._register_parameters(meas, param_meas,
                              setpoints=all_setpoint_params,
                              shapes=None)
    doNd._register_actions(meas, enter_actions, exit_actions)

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasaver:

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)
        timer.reset_clock()

        while True:
            time.sleep(delay)
            datasaver.add_result(
                (timer, timer.get()),
                *doNd.process_params_meas(param_meas,
                                           use_threads=use_threads),
                *additional_setpoints_data
            )
            if (timeout - timer.get()) < 0.005:
                break
        dataset = datasaver.dataset

    return doNd._handle_plotting(dataset, do_plot, interrupted())

def sweepfield(magnet: _BaseParameter,
               field_target: float,
               delay: float,
               *param_meas: doNd.ParamMeasT,
               exp: Optional[Experiment] = None,
               measurement_name: Optional[str] = None,
               do_plot: Optional[bool] = None,
               use_threads: Optional[bool] = False,
               enter_actions: doNd.ActionsT = (),
               exit_actions: doNd.ActionsT = (),
               additional_setpoints=tuple()):

    meas = Measurement(exp=exp, name=measurement_name)
    timer = TimeParameter("time")
    swr = magnet.magnet_sweeprate()
    field_init = magnet.Bz()
    timeout = (field_target - field_init)/swr*60

    all_setpoint_params = (timer,) + tuple(
        s for s in additional_setpoints)

    measured_parameters = list(param for param in param_meas
                               if isinstance(param, _BaseParameter))

    if not use_threads:
        use_threads = False
    elif len(measured_parameters) > 2 or use_threads:
        use_threads = True
    else:
        use_threads = False

    doNd._register_parameters(meas, all_setpoint_params)
    doNd._register_parameters(meas, param_meas,
                              setpoints=all_setpoint_params,
                              shapes=None)
    doNd._register_actions(meas, enter_actions, exit_actions)

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasaver:

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)
        timer.reset_clock()
        magnet.Bz(field_target)

        while True:
            time.sleep(delay)
            datasaver.add_result(
                (timer, timer.get()),
                *doNd.process_params_meas(param_meas,
                                           use_threads=use_threads),
                *additional_setpoints_data
            )
            if (timeout - timer.get()) < 0.005:
                break
        dataset = datasaver.dataset

    return doNd._handle_plotting(dataset, do_plot, interrupted())


def sweep2d(
    param_setx: _BaseParameter,
    xarray,
    inner_delay: float,
    param_sety: _BaseParameter,
    yarray,
    outer_delay: float = .1,
    *param_meas: doNd.ParamMeasT,
    exp: Optional[Experiment] = None,
    measurement_name: Optional[str] = None,
    do_plot: Optional[bool] = None,
    use_threads: Optional[bool] = None,
    outer_enter_actions: doNd.ActionsT = (),
    outer_exit_actions: doNd.ActionsT = (),
    inner_enter_actions: doNd.ActionsT = (),
    inner_exit_actions: doNd.ActionsT = (),
    measure_retrace: Optional[bool] = False,
    num_retrace: Optional[str] = 201,
    additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
):

    meas = Measurement(exp=exp, name=measurement_name)
    meas_retrace = Measurement(exp=exp, name=f'{measurement_name}_retrace')

    all_setpoint_params = (param_sety, param_setx,) + tuple(
        s for s in additional_setpoints
    )

    measured_parameters = tuple(param for param in param_meas
                                if isinstance(param, _BaseParameter))

    if use_threads:
        _use_threads = True
    elif len(measured_parameters) > 2 or use_threads:
        _use_threads = True
    else:
        _use_threads = False

    try:
        if measure_retrace:
            loop_shape = tuple(
                1 for _ in additional_setpoints) + (len(yarray), len(xarray))
        else:
            loop_shape = tuple(
                1 for _ in additional_setpoints) + (len(yarray)*2, len(xarray))
        shapes: Shapes = detect_shape_of_measurement(
            measured_parameters,
            loop_shape
        )
    except TypeError:
        warn(f" shape of {measured_parameters} unknown ")
        shapes = None

    doNd._register_parameters(meas, all_setpoint_params)
    doNd._register_parameters(meas, param_meas, setpoints=all_setpoint_params,
                              shapes=shapes)
    doNd._register_actions(meas, outer_enter_actions, outer_exit_actions)

    doNd._register_parameters(meas_retrace, all_setpoint_params)
    doNd._register_parameters(meas_retrace, param_meas,
                              setpoints=all_setpoint_params,
                              shapes=shapes)
    doNd._register_actions(meas_retrace, outer_enter_actions,
                           outer_exit_actions)
    param_setx.post_delay = 0.0
    param_sety.post_delay = 0.0

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasweep, \
            meas_retrace.run(write_in_background=True) as dataretrace:

        print(f'sweeps: {datasweep.run_id}, retrace: {dataretrace.run_id}')

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)

        for c, set_pointy in enumerate(tqdm(yarray)):
            _safesweep_to(set_pointy, param_sety)

            if c % 2 == 1 and measure_retrace:
                xsetpoints = xarray[::-1]
                datasaver = dataretrace
            else:
                xsetpoints = xarray
                datasaver = datasweep

            _safesweep_to(xsetpoints[0], param_setx)
            time.sleep(outer_delay)

            for action in inner_enter_actions:
                action()

            for set_pointx in xsetpoints:
                _safesweep_to(set_pointx, param_setx)
                time.sleep(inner_delay)

                datasaver.add_result(
                    (param_sety, set_pointy),
                    (param_setx, set_pointx),
                    *doNd.process_params_meas(param_meas,
                                              use_threads=_use_threads),
                    *additional_setpoints_data
                    )
                for action in inner_exit_actions:
                    action()

    return doNd._handle_plotting(datasweep.dataset, do_plot, interrupted()), \
        doNd._handle_plotting(dataretrace.dataset, do_plot, interrupted())


def sweepfield2d(
    magnet: _BaseParameter,
    field_target: float,
    delay: float,
    param_sety: _BaseParameter,
    yarray,
    outer_delay: float = .1,
    *param_meas: doNd.ParamMeasT,
    exp: Optional[Experiment] = None,
    measurement_name: Optional[str] = None,
    do_plot: Optional[bool] = None,
    use_threads: Optional[bool] = None,
    outer_enter_actions: doNd.ActionsT = (),
    outer_exit_actions: doNd.ActionsT = (),
    inner_enter_actions: doNd.ActionsT = (),
    inner_exit_actions: doNd.ActionsT = (),
    measure_retrace: Optional[bool] = False,
    num_retrace: Optional[str] = 201,
    additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
):

    timer = TimeParameter("time")
    swr = magnet.magnet_sweeprate()
    field_init = magnet.Bz()
    timeout = (field_target - field_init)/swr*60
    inner_enter_actions = (magnet.Bz, field_target),
    inner_exit_actions = [(magnet.Bz, field_init),(time.sleep, timeout)],

    all_setpoint_params = (timer,) + tuple(
        s for s in additional_setpoints)

    measured_parameters = list(param for param in param_meas
                               if isinstance(param, _BaseParameter))
    meas = Measurement(exp=exp, name=measurement_name)
    meas_retrace = Measurement(exp=exp, name=f'{measurement_name}_retrace')

    all_setpoint_params = (param_sety, param_setx,) + tuple(
        s for s in additional_setpoints
    )

    measured_parameters = tuple(param for param in param_meas
                                if isinstance(param, _BaseParameter))

    if use_threads:
        _use_threads = True
    elif len(measured_parameters) > 2 or use_threads:
        _use_threads = True
    else:
        _use_threads = False

    try:
        if measure_retrace:
            loop_shape = tuple(
                1 for _ in additional_setpoints) + (len(yarray), len(xarray))
        else:
            loop_shape = tuple(
                1 for _ in additional_setpoints) + (len(yarray)*2, len(xarray))
        shapes: Shapes = detect_shape_of_measurement(
            measured_parameters,
            loop_shape
        )
    except TypeError:
        warn(f" shape of {measured_parameters} unknown ")
        shapes = None

    doNd._register_parameters(meas, all_setpoint_params)
    doNd._register_parameters(meas, param_meas, setpoints=all_setpoint_params,
                              shapes=shapes)
    doNd._register_actions(meas, outer_enter_actions, outer_exit_actions)

    doNd._register_parameters(meas_retrace, all_setpoint_params)
    doNd._register_parameters(meas_retrace, param_meas,
                              setpoints=all_setpoint_params,
                              shapes=shapes)
    doNd._register_actions(meas_retrace, outer_enter_actions,
                           outer_exit_actions)
    param_setx.post_delay = 0.0
    param_sety.post_delay = 0.0

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasweep, \
            meas_retrace.run(write_in_background=True) as dataretrace:

        print(f'sweeps: {datasweep.run_id}, retrace: {dataretrace.run_id}')

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)

        for c, set_pointy in enumerate(tqdm(yarray)):
            _safesweep_to(set_pointy, param_sety)

            if c % 2 == 1 and measure_retrace:
                B = field_init
                datasaver = dataretrace
            elif c % 2 == 0 and not measure_retrace:
                B = field_target
                magnet.Bz(B)
                time.sleep(timeout)
            else:
                B = field_target
                datasaver = datasweep
            time.sleep(outer_delay)

            for action in inner_enter_actions:
                action()
            timer.reset_clock()
            magnet.Bz(B)

            while True:
                time.sleep(inner_delay)
                datasaver.add_result(
                    (param_sety, set_pointy),
                    (param_setx, set_pointx),
                    *doNd.process_params_meas(param_meas,
                                              use_threads=_use_threads),
                    *additional_setpoints_data
                    )
                if (timeout - timer.get()) < 0.005:
                    break
            for action in inner_exit_actions:
                action()

    return doNd._handle_plotting(datasweep.dataset, do_plot, interrupted()), \
        doNd._handle_plotting(dataretrace.dataset, do_plot, interrupted())
