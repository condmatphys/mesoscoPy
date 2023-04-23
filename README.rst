mesoscoPy
=========

|DOCS| |python versions|

MesoscoPy is a library of utils to run experiment in mesoscopic physics. It runs with qCoDeS.
To learn more about the synatx, read `First steps with mesoscoPy <https://condmatphys.github.io/mesoscoPy/start/first-steps.html>`__.

Install
=======

Refer to `our documentation <https://condmatphys.github.io/mesoscoPy/start/installation.html>`__ for installation.

Documentation
=============

Read it `here <https://condmatphys.github.io/mesoscoPy/>`__.
Documentation is updated and deployed on every successful build in master.
We use sphinx for the documentation. To build the documentation locally, make sure that you have the extra dependencies required:

.. code:: bash

   pip install -r docs_requirements.txt

Go to the directory ``docs`` and type:

.. code:: bash

   make html

It generates the documenation with rendered html in  ``docs/_build/html``.

Contributing
============

As mesoscoPy is still a project in its infancy, we have no strict rules for contribution. However, please make sure you test your code before pushing to the ``main`` branch.


License
=======

See `License <https://github.com/condmatphys/mesoscoPy/tree/master/LICENSE>`__.


.. |python versions| image:: https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue.svg
.. |DOCS| image:: https://img.shields.io/badge/read%20-thedocs-ff66b4.svg
   :target: http://condmatphys.github.io/mesoscoPy