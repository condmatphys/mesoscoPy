.. mesoscoPy documentation master file, created by
   sphinx-quickstart on Thu Nov 18 12:29:26 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

mesoscoPy's documentation
=========================


mesoscoPy is a high level program to run electron transport experiments. It was
designed with the Manchester setup in mind, but can easily be adapted to a
variety of different cryostats and measurement equipments.

This documentation describe the installation of the program, and steps to run
experiments in transport physics. This kind of experiments are usually composed
of DC voltage and current sources, lock-in amplifiers and a cryostat or dilution
refrigerator equipped with a superconducting magnet. mesoscoPy allows the use of
multiple equipments to perform this kind of measurements.


.. toctree::
   :maxdepth: 1
   :caption: Getting started

   start/overview
   start/installation
   start/first-steps
   .. start/issue
   start/faq
   start/changelog

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   user/instrument
   user/measurement
   user/experiment
   user/analysis

.. toctree::
   :maxdepth: 1
   :caption: Examples

   examples/halleffect
   examples/josephson

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

License
-------

.. include:: ../LICENSE
