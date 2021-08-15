"""
Some utils used in sweeps
"""

import numpy as np
from warnings import warn


def generate_sweep_array(start, stop, step=None, num=None, tol=1e-10):
    """
    generate an array over a specified interval.
    requires <start> and <stop> and either <step> or <num>
    args:
        start (Union[int, float]): starting value fof the sequence
        stop(Union[int, float]): end value of sequence
        step (Optional[Union[int, float]]): spacing between values
        num (Optional[int]): number of values to generate.
        tol (Optional[float]): step size tolerance. Taken into account
        only if a step size is given.
    returns:
        numpy.ndarray: numbers over the specified interval.
    """

    if step and num:
        raise AttributeError("use of step and num at the same time.")
    if (step is None) and (num is None):
        raise ValueError("specify either a step size (`step=[float]`) or a "
                         "number of steps (`num=[int]`)."
                         )

    if step is not None:
        steps = abs((stop - start) / step)
        steps_lo = int(np.floor(steps + tol))
        steps_hi = int(np.ceil(steps - tol))

        if steps_lo != steps_hi:
            real_step = abs((stop - start) / (steps_lo + 1))
            if abs(step - real_step) / step > 0.05:
                warn(
                    "Could not find an integer number of points for "
                    "the given `start`, `stop`, and `step`={0}. "
                    "Effective step size is `step`={1:.4f}".format(step,
                                                                   real_step)
                     )
        num = steps_lo + 1
    return np.linspace(start, stop, num=num)
