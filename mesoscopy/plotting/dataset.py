"""
functions to plot datasets
"""

from typing import Union, Any, Tuple
import matplotlib.pyplot as plt

from qcodes.dataset.plotting import (
    _complex_to_real_preparser, _set_data_axes_labels,
    _rescale_ticks_and_units, _appropriate_kwargs, plot_on_a_plain_grid
)

from ..analysis.load import list_parameters, get_dataset, get_data_by_paramname


def plot_dataset_2D(id: Union[int, str],
                    var: str,
                    rescale_axes: bool = True,
                    multiply_by: Tuple[float, float, float] = (1, 1, 1),
                    complex_plot_type: str = 'mag_and_phase',
                    complex_plot_phase: str = 'degrees',
                    size=8,
                    **kwargs: Any):
    """
    Make a 2D plot for a given dataset.
    The plot has a title that comprises run id, measurement name and
    run timestamp.

    ``**kwargs`` passed to matplotlib's plotting function.

    Args:
        id: either run_id or guid
        var: variable to plot
        rescale_axes: True: tick labels and units of parameters are rescaled:
            0.001V becomes 1mV.
        multiply_by: rescale axes with a factor. takes tuple for (x,y,z)
        complex_plot_type: convert compleox-valued parameters to two
            real-valued parameters. takes either ``"real_and_imag"`` or
            ``"mag_and_phase"``
        complex_plot_phase: if plotting complex with type ``"mag_and_phase"``,
            takes either ``"radians"`` or ``"degrees"``.

    Returns:
        axes and colorbar handles

    TODO:
        * rewrite so that it can be supplied with matplotlib axes or list of
        axes, with colorbar axes.
    """

    if complex_plot_type not in ['real_and_imag', 'mag_and_phase', 'real',
                                 'imag', 'mag', 'phase']:
        raise ValueError(
            f'Invalid complex plot type given. Received {complex_plot_type} '
            'but can only accept "real_and_imag" or "mag_and_phase".')
    if complex_plot_phase not in ['radians', 'degrees']:
        raise ValueError(
            f'Invalid complex plot phase given. Received {complex_plot_phase} '
            'but can only accept "degrees" or "radians".')
    degrees = complex_plot_phase == "degrees"

    if complex_plot_type == 'real' or complex_plot_type == 'imag':
        complex_type = 'real_and_imag'
    elif complex_plot_type == 'mag' or complex_plot_type == 'phase':
        complex_type = 'mag_and_phase'
    else:
        complex_type = complex_plot_type

    dat = get_dataset(id)
    run_id = dat._run_id
    meas_name = dat.name
    timestamp = dat.run_timestamp()
    title = f'[ #{run_id}: {meas_name} - {timestamp} ]'

    variables = list_parameters(id, print=False, out=True)
    if var not in variables['dependent']:
        raise ValueError(f'{var} should be in {variables["dependent"]}')
    dataset = get_data_by_paramname(dat, var)
    dataset = _complex_to_real_preparser([dataset],
                                         conversion=complex_type,
                                         degrees=degrees)

    x = dataset[0][0]['name']
    y = dataset[0][1]['name']

    if complex_plot_type == 'real' or complex_plot_type == 'mag':
        dataset = [dataset[0]]
    elif complex_plot_type == 'imag' or complex_plot_type == 'phase':
        try:
            dataset = [dataset[1]]
        except ValueError:
            print('the dataset had no imaginary part')

    nplots = len(dataset)

    print('plot_dataset_2D:\n'
          f'X_axis: {x}\t Y_axis: {y}\t Z_axis: {var}')

    fig, axeslist = plt.subplots(nplots, figsize=(size, .7*size*nplots))

    colorbars = [None]*nplots
    for data, ax, colorbar in zip(dataset, axeslist, colorbars):
        X = data[0]['data']
        Y = data[1]['data']
        Z = data[2]['data']
        shape = data[2]['shape']

        X.reshape(shape)
        Y.reshape(shape)
        Z.reshape(shape)

        with _appropriate_kwargs("2D_grid",
                                 colorbar is None, **kwargs) as k:
            ax, colorbar = plot_on_a_plain_grid(X*multiply_by[0],
                                                Y*multiply_by[1],
                                                Z*multiply_by[2],
                                                ax, colorbar,
                                                **k)
        _set_data_axes_labels(ax, data, colorbar)
        if rescale_axes:
            _rescale_ticks_and_units(ax, data, colorbar)

        ax.set_title(title)
        plt.tight_layout()

    return axeslist, colorbars
