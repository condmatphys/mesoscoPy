.. _overview:

Overview
========

.. toctree::
   :maxdepth: 2

mesoscoPy is a high-level interface for transport measurements, based on
`QCoDeS <https://qcodes.github.io/Qcodes/index.html>`_. It enables you to control
equipments to perform electron transport measurements in a quick and easy way.

It was designed with the Manchester's National Graphene Institute's setup in
mind, but can easily be adapted to a variety of different cryostats and
measurement equipments.

The experiments are usually composed of DC voltage and current sources, lock-in
amplifiers and cryostats/dilution refrigerators, equipped with superconduciting
magnets. *mesoscoPy* allows to control multiple equipments simultaneously to
acquire and process data.

At the moment, *mesoscoPy* allows the use of the following equipments:

- **Lock-in amplifiers**: Zurich Instruments MFLI, SRS 830 (work in progress)
- **DC voltage source**: Keithley 2400 and 2600 series
- **cryostats & superconducting magnets**: Oxford Instruments Triton
  (temperature + magnet), Oxford
  Instruments Mercury iPS (magnet), Oxford Instruments Mercury iTC
  (temperature).
- **Signal generator**: R&S SMB 100A

A number of other instruments can be added, thanks to the use of QCoDeS as a low
level background interface.

*mesoscoPy* offers a unified model for viewing and handling measurement sweeps
and aps. It saves all the data in SQL databases, that can be easily accessed,
and the data easily plot.

example
-------

The following code shows an example of python code to measure 2 lock-ins while
sweeping a voltage source gate using *mesoscoPy*'s high level programming
construct.

.. code:: python

   import mesoscopy
   station = mesoscopy.init_station(
       '4400', '4401',
       SMU_addr='TCPIP::192.168.0.2::inst0::INSTR'
   )

   mesoscopy.init_lockin(station, freq=127, ampl=2)

   xvals = mesoscopy.generate_lin_array(10, -10, step=.1)

   mesoscopy.measurement.sweep1d(
        station.keithley.smua.volt,
        xvals,
        1.6,
        station.mf4400.demods[0].sample,
        station.mf4401.demods[0].sample,
    )

.. _releases:

mesoscoPy Releases
------------------

mesoscoPy is still a software in development. It was mostly designed with one
experimental setup in mind, therefore may not be exactly suited for your
experiment. If you have any feature request, please do it `on github
<https://github.com/julienbarrier/mesoscoPy/issues>`_.
