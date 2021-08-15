# import qcodes as qc
import numpy as np

from qcodes.dataset.measurements import Measurement
from qcodes.instrument.base import Instrument
from qcodes.instrument.parameter import Parameter
from qcodes.dataset.plotting import plot_dataset
from ..instrument.instrument_tools import create_instrument
from qcodes.instrument_drivers.oxford.triton import Triton


def sweep_current_keithley2450_to(self, target, *arg, **kwarg):
    steps = kwarg.pop('steps', 10)
    parameters = kwarg.pop('parameters', [])
    # print(len(parameters))

    self.source.function.set('current')
    self.sense.function.set('voltage')
    self.output_enabled.set(True)
    init_i = self.source.current()

    set_i = np.zeros(steps)
    get_v = np.zeros(steps)
    get_p = np.zeros(2)

    for step in range(steps):
        set_i[step] = init_i + (target-init_i)/(steps-1)*step
        self.source.current(set_i[step])
        get_v[step] = self.sense.voltage()

    if 'parameters' in kwarg:
        get_p = np.zeros(len(parameters))
        for p in range(len(get_p)):
            get_p[p] = parameters[p].get()
    return set_i, get_v, get_p

triton = create_instrument(Triton, "triton", address="192.168.0.2", port=33576,
                           force_new_instance=True)

def contact_IV(self, start=-50e-9, stop=50e-9, steps=51, cn=1,
               oi_triton=triton, **kwarg):
    exp = kwarg.pop('exp', 'experiment')
    # oi_triton = kwarg.pop('triton', triton)
    # global triton
    contact = Parameter(name='contact', label='contact being tested')

    self.reset()
    self.terminals.set('front')
    self.source_function.set('current')
    self.sense_function.set('voltage')
    self.sense.four_wire_measurement.set(False)
    self.output_enabled.set(True)
    self.sense.range.set(0.2)
    self.source.range.set(1e-7)

    sweep_current_keithley2450_to(self, start)
    m = Measurement(exp=exp, name='contact {cn}')

    m.register_parameter(self.source.current,
                         paramtype='array')
    m.register_parameter(self.sense.voltage,
                         setpoints=(self.source.current,),
                         paramtype='array')
    m.register_parameter(oi_triton.T5,
                         paramtype='numeric')
    m.register_parameter(oi_triton.T8,
                         paramtype='numeric')
    m.register_parameter(contact,
                         paramtype='numeric')

    with m.run() as datasaver:
        set_i, get_v, get_p = sweep_current_keithley2450_to(
            self,
            stop,
            steps=steps,
            parameters=[triton.T5, triton.T8]
        )
        datasaver.add_result(
            (self.source.current, set_i),
            (self.sense.voltage, get_v),
            (triton.T5, get_p[0]),
            (triton.T8, get_p[1]),
            (contact, cn)
        )
    sweep_current_keithley2450_to(self, 0)

    self.output_enabled.set(False)

    dataset = datasaver.dataset
    plot_dataset(dataset)
    return None
