.. _halleffect:

Hall Effect characterisation
============================

.. toctree::
   :maxdepth: 2


Let's start with a double gated Hall bar. The two gates are connected to a
keithley 2600 series sourcemeter. We source a current with a lock-in MFLI (say,
id 4400, and we measure the longitudinal resistance with the same lock-in, and
the Hall resistance with another one, say 4401. The magnet is an Oxford
Instruments triton.

Initialisation
--------------

.. code:: python
    
   import mesoscopy
   mesoscopy.init_db('../database_hallbar.db')
   exp = mesoscopy.create_exp(
        experiment_name='Hall bar gate dependence',
        sample_name='test sample'
   )
   station = mesoscopy.init_station(
        '4400', '4401',
        SMU_addr='TCPIP::192.168.0.1::inst0::INSTR',
        triton_addr='192.168.0.2'
   )

   mesoscopy.init_smu(
        station,
        limits_v=[16,48],
        max_rate=[.08,.12]
   )
   mesoscopy.init_lockin(
        station,
        freq=117,
        ampl=1,
        filterorder=8)


Density calibration
-------------------


Gate map
--------


Fan diagram at constant displacement
------------------------------------
