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

From windows, installation is straightforward. On a linux machine, run ```sudo
apt install ./rsvisa.deb``` (ubuntu-linux), and edit the file ```~/.pyvisarc```
as:

.. code:: text
   [Paths]

    VISA library: /usr/lib/librsvisa.so


Then, you can download the latest version of mesoscoPy. Select the latest
release from `this link <https://github.com/julienbarrier/mesoscoPy/releases>`_.
Alternatively, you may clone the git repository, but beware that this may
present some instabilities.

Installation
------------

In *Anaconda Prompt*, go to the mesoscopy folder with the ```cd``` command. Once
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


Use remotely
------------

jupyter notebook --generate-config
then jupyter lab password



