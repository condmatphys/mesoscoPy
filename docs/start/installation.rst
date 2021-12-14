.. _install:

Install mesoscoPy
=================

.. toctree::
   :maxdepth: 2

Requirements
------------

You need a working python 3.9 environment to use mesoscoPy. It is strongly
advised to install a disrtibution like anaconda. For this, install it following
`these instructions <https://docs.anaconda.com/anaconda/install/index.html>`_.
Make sure to download the latest version with python 3.9 or newer.

Once you've installed Anaconda, open the *Anaconda Prompt* and type in:

.. code:: bash

   conda install -c conda-forge jupyterlab
   conda install -c conda-forge nb_conda_kernels
   conda install pip

This will install a few required packages on your Anaconda distribution.

In addition, you will need a visa library. We are working with `RS Visa
<https://www.rohde-schwarz.com/uk/applications/r-s-visa-application-note_56280-148812.html>`_.

From windows, installation is straightforward. On a linux machine, run ``sudo
apt install ./rsvisa.deb`` (ubuntu-linux). Then, you need to make sure that
pyvisa is linked to RS Visa. There are instructions on `PyVISA's
documentation <https://pyvisa.readthedocs.io/en/latest/introduction/configuring.html>`_.
In pratice, you should edit the file ``~/.pyvisarc`` with something like:

.. code:: text

   [Paths]

    VISA library: /usr/lib/librsvisa.so

See the `PyVISA documentation
<https://pyvisa.readthedocs.io/en/latest/advanced/backends.html>`_ for more
information.

Then, you can download the latest version of mesoscoPy. Select the latest
release from `this link <https://github.com/julienbarrier/mesoscoPy/releases>`_.
Alternatively, you may clone the git repository, but beware that this may
present some instabilities.

Installation
------------

In *Anaconda Prompt*, go to the mesoscopy folder with the ``cd`` command. Once
you're in the folder of interest, run:

.. code:: bash

   conda env create -f environment.yml
   conda activate mesoscopy
   pip install .

This will create a *Conda* environment named mesoscopy, install the required
dependencies and install mesoscopy on your machine. Note the last period
indicates the folder of interest. If you want to install in edit-mode, run

.. code:: bash

    pip install -e .

instead. When you want to update, you may run the following:

.. code:: bash

    conda env update --file environment.yml --prune
    pip install --upgrade mesoscopy


You are now ready to use *mesoscoPy* from a jupyter notebook. Follow the steps
in the next page for an overview of how to proceed. If you want to use
*mesoscoPy* remotely, follow the steps below.

Use remotely
------------

You will need to configure `jupyterlab
<https://jupyterlab.readthedocs.io/en/stable/>`_ to allow remote access.

First, run in the Prompt:

.. code:: bash

   jupyter lab --generate-config

This will tell you the location of the configuration file to edit. You will add
the following lines at the end of this file:

.. code:: python

    c.NotebookApp.allow_password_change = False
    c.NotebookApp.allow_remote_access = True
    c.NotebookApp.ip = '*'
    c.NotebookApp.open_browser = False
    c.NotebookApp.port = 8888

Finally, run the following in your prompt:

.. code:: bash

   jupyter lab password

This will generate a password for remote secure access.
To access the *JupyterLab* instance, connect to a computer and type:
``http://[HOST]:8888`` where [HOST] is the IP address of the computer running
*mesoscoPy*.

You are now ready to use *mesoscoPy*
