"""
sweep functions
"""

import time
from typing import (Optional, Sequence)
from warnings import warn
from qcodes.dataset.measurements import Measurement
from qcodes.dataset.experiment_container import Experiment
from qcodes.instrument.parameter import _BaseParameter
from qcodes.dataset.descriptions.detect_shapes import \
    detect_shape_of_measurement
from qcodes.utils.dataset import doNd
from ._utils import _is_monotonic
from tqdm.auto import tqdm

def sweep1d(param_set: _BaseParameter,
            xarray,
            delay: float,
            *param_meas: doNd.ParamMeasT,
            exp: Optional[Experiment] = None,
            use_threads: Optional[bool] = None,
            enter_actions: doNd.ActionsT = (),
            exit_actions: doNd.ActionsT = (),
            additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
            ):

    if not _is_monotonic(xarray):
        warn('The array over which sweep is being made is not monotonic.')

    meas = Measurement(exp=exp)

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

def Sweep1D_repeat(
    param_set: _BaseParameter,
    xarray,
    inner_delay: float,
    *param_meas: doNd.ParamMeasT,
    num_repeat: int = 1,
    outer_delay: float = .1,
    exp: Optional[Experiment] = None,
    use_threads: Optional[bool] = None,
    outer_enter_actions: doNd.ActionsT = (),
    outer_exit_actions: doNd.ActionsT = (),
    inner_enter_actions: doNd.ActionsT = (),
    inner_exit_actions: doNd.ActionsT = (),
    measure_retrace: Optional[bool] = False,
    additional_setpoints: Sequence[doNd.ParamMeasT] = tuple(),
):

    if not _is_monotonic(xarray):
        warn('The array over which sweep is being made is not monotonic.')

    meas = Measurement(exp=exp)

    outer_count = CountParameter('repeat')
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
    doNd._register_actions(meas, inner_enter_actions, inner_exit_actions)

    param_set.post_delay = 0.0

    with doNd._catch_keyboard_interrupts() as interrupted, \
        meas.run(write_in_background=True) as datasaver:

        additional_setpoints_data = doNd.process_params_meas(
            additional_setpoints)
        for i in range(num_repeat):
            y = outer_count.get()
            if y % 2 == 0:
                xsetpoints = xarray
            else:
                xsetpoints = xarray[::-1]

    for set_point in tqdm(xarray):
param_set.set(set_point)
time.sleep(inner_delay)
datasaver.add_result(
    (param_set, set_point),
    *doNd.process_params_meas(param_meas,
                              use_threads=use_threads),
    *additional_setpoints_data
)
dataset = datasaver.dataset


return dataset
