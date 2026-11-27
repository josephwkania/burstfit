# burstfit

[![GitHub issues](https://img.shields.io/github/issues/thepetabyteproject/burstfit?style=flat-square)](https://github.com/thepetabyteproject/burstfit/issues)
[![GitHub forks](https://img.shields.io/github/forks/thepetabyteproject/burstfit?style=flat-square)](https://github.com/thepetabyteproject/burstfit/network)
[![GitHub stars](https://img.shields.io/github/stars/thepetabyteproject/burstfit?style=flat-square)](https://github.com/thepetabyteproject/burstfit/stargazers)
[![GitHub license](https://img.shields.io/github/license/thepetabyteproject/burstfit?style=flat-square)](https://github.com/thepetabyteproject/burstfit/blob/main/LICENSE)
![ViewCount](https://views.whatilearened.today/views/github/thepetabyteproject/burstfit.svg)
![GitHub Workflow Status](https://img.shields.io/github/workflow/status/thepetabyteproject/burstfit/Python%20package?style=flat-square)

![PyPI - Python Version](https://img.shields.io/pypi/pyversions/burstfit?style=flat-square)
![PyPI](https://img.shields.io/pypi/v/burstfit?style=flat-square)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)
[![codecov](https://codecov.io/gh/thepetabyteproject/burstfit/branch/main/graph/badge.svg?style=flat-square)](https://codecov.io/gh/thepetabyteproject/burstfit)

Spectro-temporal modeling of FRBs

# Installation
You can install `burstfit` directly using `pip`

```bash
pip install burstfit
```
Or if you want to try out the latest stuff,
```bash
git clone https://github.com/thepetabyteproject/burstfit
cd burstfit
pip install .
```
BurstFit needs Python 3.11 or newer.

For reproducible results (for example, in a pipeline), install with the pinned numerical stack:
```bash
pip install -c constraints/pipeline.txt .
```
See `constraints/pipeline.txt` for what is pinned and why.

## Reproducing results from BurstFit 0.1.0
Fits made with BurstFit 0.1.0 (your 0.6.7, NumPy 1.x, SciPy <= 1.10) can be reproduced bit-for-bit on
Python 3.11-3.12:
```bash
pip install -c constraints/exact-legacy.txt .
```
```python
bd = BurstData(..., flag_rfi=True, spectral_kurtosis_legacy_mad=True)  # needs a your with this option
bf = BurstFit(..., legacy_spectra_window=True)
```
Run on the same kind of machine as the original fits: whether the CPU has AVX-512, and the C library
(glibc), change the last bits, and multi-component fits amplify that. See `constraints/exact-legacy.txt`
for details.

# Documentation
Have a look at our [docs](https://thepetabyteproject.github.io/burstfit/) for the documentation.

# Tutorials
Here are some [tutorial notebooks](https://github.com/thepetabyteproject/burstfit/tree/main/examples) to get you started.

**Note**:
To run the tutorial notebooks you would need to install `jupyter`.

# Citation

Please cite the following paper if you use `burstfit`: 

```bash
@ARTICLE{2021arXiv210705658A,
       author = {{Aggarwal}, Kshitij and {Agarwal}, Devansh and {Lewis}, Evan F. and {Anna-Thomas}, Reshma and {Cardinal Tremblay}, Jacob and {Burke-Spolaor}, Sarah and {McLaughlin}, Maura A. and {Lorimer}, Duncan R.},
        title = "{Comprehensive analysis of a dense sample of FRB 121102 bursts}",
      journal = {arXiv e-prints},
     keywords = {Astrophysics - High Energy Astrophysical Phenomena, Astrophysics - Instrumentation and Methods for Astrophysics},
         year = 2021,
        month = jul,
          eid = {arXiv:2107.05658},
        pages = {arXiv:2107.05658},
archivePrefix = {arXiv},
       eprint = {2107.05658},
 primaryClass = {astro-ph.HE},
       adsurl = {https://ui.adsabs.harvard.edu/abs/2021arXiv210705658A},
      adsnote = {Provided by the SAO/NASA Astrophysics Data System}
}
```

