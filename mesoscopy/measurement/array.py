import numpy as np
from warnings import warn

from ..analysis.math import Vrf2dBm


def generate_lin_array(start, stop, step=None, num=None, tol=1e-10):
    """
    generate an array over a specified interval.
    requires <start> and <stop> and either <step> or <num>
    args:
        start (Union[int, float]): starting value fof the sequence
        stop(Union[int, float]): end value of sequence
        step (Optional[Union[int, float]]): spacing between values
        num (Optional[int]): number of values to generate.
        tol (Optional[float]): step size tolerance.
    returns:
        numpy.ndarray: numbers over the specified interval.
    """

    if step and num:
        raise AttributeError("use of step and num at the same time.")
    if (step is None) and (num is None):
        raise ValueError("specify either a step size (`step=[float]`) or a "
                         "number of steps (`num=[int]`).")

    if step is None:
        step_size = abs((stop - start) / num)
        if step_size < tol:
            real_num = int(np.floor(abs((stop - start) / tol) + tol)) + 1
            real_step = abs((stop - start) / real_num)
            warn(
                "Could not generate an array with so many steps. "
                "Effective step size is `step`={1.4f}, "
                "Effective number of steps is `num`={0}".format(real_step,
                                                                real_num))
        else:
            real_num = num
        return np.linspace(start, stop, num=real_num)

    else:
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
                                                                   real_step))
        num = steps_lo + 1
        return np.linspace(start, stop, num=num)


def generate_RF_array(start, stop, step=None, num=None, tol=1e-10,
                      attenuation=45):
    if Vrf2dBm(start, attenuation) < -30:
        warn('`start` is below the minimum value of -30dBm')
    elif Vrf2dBm(stop, attenuation) > 25:
        warn('`stop` is above the maximum value of 25dBm')
    rfa = generate_lin_array(start, stop, step=step, num=num, tol=tol)
    return Vrf2dBm(rfa, attenuation)


def generate_1D_sweep_array(start, stop, step=None, num=None, tol=1e-10):
    ''' function for backward compatibility
    '''
    return generate_lin_array(start, stop, step=step, num=num, tol=tol)
