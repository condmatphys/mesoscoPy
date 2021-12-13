.. _josephson:

Josephson effect
================

.. toctree::
   :maxdepth: 2


Let's start with a 4-terminal Josephson junction. The drain contact is connected
to a MFLI lock-in via an AC-DC mixer. The AC current is sourced via the MFLI
Voltage input, the DC current via the Auxiliary output 1 of the MFLI.
The device is also exposed to an RF excitation, sourced from a R&S SMB 100A.

Initialisation
--------------

.. code:: python
    
   import mesoscopy
   mesoscopy.init_db('../database_josephson.db')
   station = mesoscopy.init_station(
        '4400', '4401',
        rf_addr='TCPIP::192.168.0.3::inst0::INSTR',
        triton_addr='192.168.0.2'
   )

   mesoscopy.init_lockin(
        station,
        freq=117,
        ampl=2,
        filterorder=8)


D.C. Josephson effect
---------------------

We can start with the d.c. Josephson effect. At first, we initialise our
experiment:

.. code:: python

   exp = mesoscopy.create_exp(
        experiment_name='d.c. Josephson effect',
        sample_name='test sample'
   )

Then, we can do a 1D sweep:

.. code:: python

   xarray = mesoscopy.generate_lin_array(1, -1, num=201)

   mesoscopy.sweep1d(
       station.mf4406.auxouts[0].offset,
       xarray,
       1.6,
       station.mf4400.demods[0].sample,
       station.mf4400.demods[2].sample,
       station.triton.B,
       station.triton.T8,
       exp=exp,
       measurement_name='Iac=2nA, Idc swept from 10 to -10nA',
       use_threads=True
   ) 

From here, many other things can be measured with the use of ``mesoscopy.sweep1d``
and ``mesoscopy.sweep2d``, for example Fraunhofer diagram, temperature
dependence, etc.


A.C. Josephson effect
---------------------

Let's start by initialising our experiment.

.. code:: python

   exp = mesoscopy.create_exp(
        experiment_name='a.c. Josephson effect',
        sample_name='test sample'
   )


At first, let's generate 2 arrays to sweep within. *mesoscoPy* can take into
account the attenuation within the line (assuming that you measured it with a
VNA), and generate an array for constant RF voltage on the device.

.. code:: python

   xarray = mesoscopy.generate_lin_array(1,-1, num=101)
   yarray = mesoscopy.generate_RF_array(15e-3,.1e-3,num=101, attenuation=42)

Here, our line has a -42dB attenuation. Now that this is generated, we can start
the map.

.. code:: python

   mesoscopy.sweep2d(
       station.mf4406.auxouts[0].offset,
       xarray, 1.6,
       station.rf_source.power,
       yarray, .1,
       station.mf4400.demods[0].sample,
       station.mf4400.demods[2].sample,
       station.triton.T8,
       exp=exp,
       measurement_name='RF power dep, Id swept from 10nA to -10nA, Iac = 2nA,',
       use_threads=True,
       measure_retrace=False
   )
