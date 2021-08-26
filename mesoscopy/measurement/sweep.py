"""
sweep functions
"""

import time
from typing import (Optional, Sequence)
from warnings import warn
from numpy import linspace
from tqdm.auto import tqdm

from qcodes.dataset.measurements import Measurement
from qcodes.dataset.experiment_container import Experiment
from qcodes.instrument.parameter import _BaseParameter
from qcodes.instrument.specialized_parameters import ElapsedTimeParameter
from qcodes.dataset.descriptions.detect_shapes import \
    detect_shape_of_measurement
from qcodes.utils.dataset import doNd

from ._utils import _is_monotonic, CountParameter


def sweep1d(param_set: _BaseParameter,
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
            param_set.set(set_point)
            time.sleep(delay)
            datasaver.add_result(
                (param_set, set_point),
                *doNd.process_params_meas(param_meas,
                                          use_threads=use_threads),
                *additional_setpoints_data
            )
        dataset = datasaver.dataset

    return dataset


def sweeptime(delay: float,
              timeout: float,
              *param_meas: doNd.ParamMeasT,
              exp: Experiment = None,
              use_threads=False,
              enter_actions: doNd.ActionsT = (),
              exit_actions: doNd.ActionsT = (),
              additional_setpoints=tuple()):

    meas = Measurement(exp=exp)
    timer = ElapsedTimeParameter("time")

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
        additional_setpoints_data = doNd._process_params_meas(
            additional_setpoints)
        timer.reset_clock()

        while True:
            time.sleep(delay)
            datasaver.add_result(
                (timer, timer.get()),
                *doNd._process_params_meas(param_meas,
                                           use_threads=use_threads),
                *additional_setpoints_data
            )
            if (timeout - timer.get()) < 0.005:
                break
        dataset = datasaver.dataset

    return dataset


def sweep1d_repeat(
    param_set: _BaseParameter,
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
    additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
):

    if not _is_monotonic(xarray):
        warn('The array over which sweep is being made is not monotonic.')

    meas = Measurement(exp=exp, name=measurement_name)
    if measure_retrace:
        meas_retrace = Measurement(exp=exp, name=f'{measurement_name}_retrace')

    outer_count = CountParameter('counter')
    all_setpoint_params = (outer_count, param_set,) + tuple(
        s for s in additional_setpoints
    )

    measured_parameters = tuple(param for param in param_meas
                                if isinstance(param, _BaseParameter))

    if not use_threads:
        use_threads = False
    elif len(measured_parameters) > 2 or use_threads:
        use_threads = True
    else:
        use_threads = False

    try:
        loop_shape = tuple(
            1 for _ in additional_setpoints) + (len(xarray),)
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

    param_set.post_delay = 0.0

    with doNd._catch_keyboard_interrupts() as interrupted, \
            meas.run(write_in_background=True) as datasweep, \
            meas_retrace.run(write_in_background=True) as dataretrace:

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)

        for i in range(num_repeat):
            y = outer_count.get()
            if y % 2 == 0:
                xsetpoints = xarray
                skip = False
                datasaver = datasweep
            elif measure_retrace:
                xsetpoints = xarray[::-1]
                skip = False
                datasaver = dataretrace
            else:
                for i in linspace(xarray[-1], xarray[0], num_retrace):
                    param_set.set(i)
                    time.sleep(.5)
                skip = True

            if not skip:
                param_set.set(xsetpoints[0])
                time.sleep(outer_delay)

                for action in inner_enter_actions:
                    action()

                for set_point in tqdm(xsetpoints):
                    param_set.set(set_point)
                    time.sleep(inner_delay)

                    datasaver.add_result(
                        (outer_count, y),
                        (param_set, set_point),
                        *doNd.process_params_meas(param_meas,
                                                  use_threads=use_threads),
                        *additional_setpoints_data
                        )
                    for action in inner_exit_actions:
                        action()

        dataset = datasaver.dataset
    return dataset


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

    if not use_threads:
        use_threads = False
    elif len(measured_parameters) > 2 or use_threads:
        use_threads = True
    else:
        use_threads = False

    try:
        loop_shape = tuple(
            1 for _ in additional_setpoints) + (len(xarray), len(yarray))
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

            if c % 2 == 0:
                xsetpoints = xarray
                skip = False
                datasaver = datasweep
            elif measure_retrace:
                xsetpoints = xarray[::-1]
                datasaver = dataretrace
                skip = False
            else:
                for i in linspace(xarray[-1], xarray[0], num_retrace):
                    param_setx.set(i)
                skip = True

            if not skip:
                param_setx.set(xsetpoints[0])
                time.sleep(outer_delay)

                for action in inner_enter_actions:
                    action()

                for set_pointx in xsetpoints:
                    param_setx.set(set_pointx)
                    time.sleep(inner_delay)

                    datasaver.add_result(
                        (param_sety, set_pointy),
                        (param_setx, set_pointx),
                        *doNd.process_params_meas(param_meas,
                                                  use_threads=use_threads),
                        *additional_setpoints_data
                        )
                    for action in inner_exit_actions:
                        action()


    return datasweep.dataset, dataretrace.dataset
