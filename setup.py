from setuptools import setup, find_packages
from mesoscopy import __version__

setup(name='mesoscopy',
      version=__version__,
      description='Library of utils to run experiments in mesoscopic physics',
      url='https://github.com/julienbarrier/mesoscopy',
      author='Julien Barrier',
      author_email='julien.barrier@manchester.ac.uk',
      classifiers=[
          "Intended Audience :: Science/Research",
          "Programming Language :: Python :: 3 :: Only",
          "License :: MIT License",
          "Topic :: Scientific/Engineering",
      ],
      license='MIT',
      packages=find_packages(),
      python_requires=">=3.9",
      install_requires=[
          "matplotlib>=3.4.0",
          "pandas>=1.3.0",
          "pyqt5>5.15.0",
          "numpy>=1.21.0",
          "qcodes==0.34.1",
          "zhinst-qcodes",
          "qcodes_contrib_drivers",
          "tqdm",
          "typing",
          "scipy",
          "pathlib"
      ],
      zip_safe=False)
