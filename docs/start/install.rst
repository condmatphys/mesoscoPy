.. _install:

Install mesoscoPy
=================

.. toctree::
   :maxdepth: 2

Requirements
------------

Before proceeding to the installation of mesoscoPy, it is advised to install a
python distribution like Anaconda.
Follow the steps here: https://docs.anaconda.com/anaconda/install/index.html 

Once you installed anaconda, you may install jupyter:
```conda install -c conda-forge jupyterlab```
```conda install -c conda-forge nb_conda_kernels```
```conda install pip```

You may need to install a visa library, like R&S visa.
sudo apt install ./rsvisa.deb from ubuntu-linux.
edit .pyvisarc accordingly.

Then, download the latest version of mesoscoPy. Alternatively, you may download
from the git, but this may be unstable.


Installation
------------

in the folder of interest:
```conda env create -f environment.yml```
```conda activate mesoscopy```
```pip install -e .```
(the last period indicates the folder of interest)

when wanting to update:
conda env update --file environment.yml --prune


Use remotely
------------

jupyter notebook --generate-config
then jupyter lab password



