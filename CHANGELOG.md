# Changelog

## 0.2.0

The last release that can reproduce fits from BurstFit 0.1.0 exactly (see "Exact-legacy mode" below).

### Python and packaging
- Requires Python 3.11 or newer; tested on 3.11–3.14, with 3.15 as an allowed failure in CI.
- Packaging moved to `pyproject.toml`; `setup.py` and `requirements.txt` are removed.
  `requirements.txt` had listed pytest and setuptools as runtime dependencies. pytest is now in the
  `tests` extra.
- Minimum versions: numpy 1.24.4, scipy 1.10.1, matplotlib 3.7.5, scikit-image 0.21.0, emcee 3.1.6,
  corner 2.2.1, your 0.6.7.
- `constraints/pipeline.txt`: exact pins for reproducible pipeline runs. With them, Python 3.11 and 3.14
  give bit-identical fits on the same machine.

### Fixes
- `np.trapz` replaced with `scipy.integrate.trapezoid`. `np.trapz` was removed in NumPy 2; the results
  are bit-identical.
- `plot_fit_results` no longer uses the removed `np.bool` alias.
- `prepare_data(mask_chans=...)` no longer fails on mixed lists such as `[(1000, 1100), 5]`, and no
  longer ignores `mask_chans=[0]`.
- `BurstData` normalisation keeps the data's dtype. NumPy 2 would promote float32 data to float64
  there; NumPy 1.x results are unchanged.

### New
- `BurstFit(..., legacy_spectra_window=True)`: use 0.1.0's spectrum window, which stops one sample
  short of the symmetric window used since 0.1.1.
- `BurstData(..., **kwargs)` passes extra keyword arguments on to `your.Candidate`.

### Exact-legacy mode
Reproduces fits made with burstfit 0.1.0, your 0.6.7, numpy 1.24 and scipy 1.10 bit-for-bit, on 50
B0355+54 test pulses:
- this release's options were checked on a machine without AVX-512;
- the same pins, with equivalent patches applied at runtime, were checked on AVX-512 nodes (Xeon Gold 6138).

It needs:
- Python 3.11–3.12 with `constraints/exact-legacy.txt` (numpy 1.26.4, scipy 1.14.1);
- `BurstData(..., spectral_kurtosis_legacy_mad=True)`, which needs a `your` with that option;
- `BurstFit(..., legacy_spectra_window=True)`;
- the same kind of machine as the original fits: AVX-512 or not, and the same glibc.

Why those pins: scipy 1.15.0 changed MINPACK `leastsq`, which the unbounded joint fit uses; numpy 2.0
changed its AVX-512 float64 code paths. Future releases will aim for statistically equivalent results,
not bit-identical ones.

### Validation
- `validation/`: the 50-pulse golden set's candidate lists and reference results, the GREENBURST production
  wrapper (`fit_one.py`, for 0.1.0 and for 0.2.0), the comparison scripts and a Slurm script.
  `VALIDATION.md` reports every check behind this release and how to rerun it.

### CI
- Tests run on Python 3.11–3.15 with pinned, oldest and latest dependencies. The tests are
  deterministic across NumPy versions.
- The docs and release workflows build from `pyproject.toml`.
