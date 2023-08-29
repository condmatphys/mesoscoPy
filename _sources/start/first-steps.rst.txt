.. _first-steps:

First steps with mesoscoPy
==========================

.. toctree::
   :maxdepth: 2


This is a short introduction, so that new users can start measuring quickly
using ``mesoscoPy``. Before you start with this code, make sure you have
properly installed and set up the Python environment, as explained on [this
page](../start/installation.rst).

Module import and database initialisation
-----------------------------------------

The first thing to do is to import ``mesoscoPy`` and load a database. If the
database does not exist yet, the init_db will first create it and then load.
Otherwise, it will simply load it.

.. code:: python

   import mesoscopy
   mesoscopy.init_db('./database.db')

Station initialisation
----------------------

In the following example, the measurement setup includes two Zurich Instruments’
MFLI lockin amplifiers (serial numbers ``mf-dev4400`` and ``mf-dev4401``), an
Oxford Mercury ITC temperature controller (on IP 192.168.0.2) and a Keithley
2614B source-measurement unit (on IP 102.168.0.13). In order to initialise the
connection to all these instruments, the basic command will be:

.. code:: python

   station = mesoscopy.init_station(
       '4400', '4401',
       MercITC_addr='TCPIP::192.168.0.2::7020::SOCKET',
       K2600_addr='TCPIP::192.168.0.13::inst0::INSTR'
   )

This will create 4 instruments: ``station.mf4400``, ``station.mf4401``,
``station.MercuryITC`` and ``station.keithley2600``. One can list all
instruments using:

.. code:: python

   station.components

Instrument initialisation
-------------------------


.. code:: python

   mesoscopy.init_smu(
       station,
       mode = ['voltage', 'voltage'],
       limits_v = [20, 50],
       limits_i = [10e-8, 50e-8],
       max_rate = [.28, .28]
   )

.. code:: python

   mesoscopy.init_mfli(
       station,
       freq = 127,
       ampl = .5,
       filterorder = 3
       sensitivity = 3e-3
   )


Start measuring
---------------

.. code:: python

   exp = mesoscopy.create_exp(
       experiment_name = 'gate dependence',
       sample_name = 'sample001'
   )


.. code:: python

   xvals = mesoscopy.generate_lin_array(10, -10, step=.1)

   mesoscopy.sweep1d(
       station.keithley2600.smua.volt,
       xvals,
       .9,
       station.mf4400.demods[0].sample,
       station.mf4401.demods[0].sample,
       station.keithley2600.smub.curr,
       station.MercuryITC.he3_temp,
       exp=exp,
       measurement_name='sweep Vg1 10V:-10V, I = 50nA, V4400:contacts 1-2, V4401: contacts 3-4, T 300mK'
   )


.. code:: python

   xvals = mesoscopy.generate_lin_array(10, -10, step=.1)
   yvals = mesoscopy.generate_lin_array(30, -30, step=.1)

   mesoscopy.sweep2d(
       station.keithley2600.smua.volt,
       xvals, .9,
       station.keithley2600.smub.volt,
       yvals, .9,
       station.mf4400.demods[0].sample,
       station.mf4401.demods[0].sample,
       station.keithley2600.smub.curr,
       station.MercuryITC.he3_temp,
       exp=exp,
       measurement_name='sweep Vg1 10V:-10V, Vg2 30V:-30V, I = 50nA, V4400:contacts 1-2, V4401: contacts 3-4, T 300mK'
   )

Plot data
---------

.. code:: python

   import matplotlib.pyplot as plt

.. code:: python

   x1, y1 = mesoscopy.analysis.load.import_sweep(1)

   fig, ax = plt.subplots()

   ax.plot(
       x1['keithley_smua_volt'],
       np.real(y1['mf4400_demods0_complex_sample'])/50e-9
   )
   ax.set_xlabel('$V_{g1}$ (V)')
   ax.set_ylabel('$R_{1-2}$ (Ω)')

