# BurstFit validation

This records what was checked when porting BurstFit from 0.1.0 (Python 3.8, NumPy 1.24, SciPy 1.10) to 0.2.0
(Python 3.11+, NumPy 2), and how to rerun each check. All results are from 2026-11-25 to 2026-11-27.

**Summary**
- **0.2.0 can reproduce 0.1.0 fits bit-for-bit.** This needs exact-legacy mode (see "How to use"), pins
  numpy 1.26.4 and scipy 1.14.1 (`constraints/exact-legacy.txt`), Python 3.11 or 3.12, and the same kind of
  machine as the reference (AVX-512 or not, same glibc).
- **Python's version never mattered.** 3.8, 3.11, 3.12, 3.13 and 3.14 give bit-identical fits when the
  numerical packages and the machine are the same.
- **The fits are chaotic.** Multi-component fits land in different, equally good minima after any last-bit
  floating-point change. That includes changes that alter no algorithm: CPU vector instructions, the C
  library, or a different summation order. So outside exact-legacy mode, results can only be compared
  statistically. From 0.2.0 on, that is the requirement: new versions should be statistically equivalent
  to these references, not bit-identical.

## Machines

| Name used here | CPU | C library |
|---|---|---|
| **AVX-512 cluster** | Intel Xeon Gold 6126 and 6138 (AVX-512) | glibc 2.17 |
| **AVX2 machine** | Intel Xeon E5-2699 v3 (Haswell: AVX2, no AVX-512) | glibc 2.39 |

Production fits were made on the AVX-512 cluster.

## Test set ("golden set")

50 FETCH-positive B0355+54 single pulses from the GREENBURST observation `data_2026-11-21_11-20-15`.

| | |
|---|---|
| Data | `chunk_452-461s.fil`: 9 s (452.000–461.000 s; samples 1765625..1800780) cut from the observation, 4096 channels × 8 bit, 256 µs. Its 256-byte header is copied unchanged, so `tstart` is the parent file's; chunk time = parent time − 452.0 s. 144 MB. The data are not distributed with this repository; `golden/chunk_452-461s.fil.sha256` identifies the exact file. |
| Candidates | `golden/batch_chunk.csv` (chunk times) and `golden/batch_orig_rows.csv` (parent-file times, as fitted in production). |
| Mix | Production fits: 11 one-component, 16 two-component and 23 three-component. One pulse (t=7.634) has a degenerate fit (DM −665), and the statistics leave it out. |
| Wrapper | `legacy/fit_one.py`, the GREENBURST production wrapper. It downsamples to 512 channels, uses per-channel median/MAD normalisation and a ±50 ms window, allows up to 3 components, and gives `curve_fit` a starting point and 5000 evaluations. Run through `run_batch.py`. |

## Reference results (`reference/`)

All are `run_batch.py` output on the golden set, in chunk times unless noted.

| File | Code and environment | Machine |
|---|---|---|
| `production_avx512.jsonl` | **Production:** burstfit 0.1.0, your 0.6.7, Python 3.8.20, numpy 1.24.4, scipy 1.10.1 (`legacy/requirements-legacy38.txt`) | AVX-512 cluster |
| `production_orig_rows.jsonl` | The same 50 rows from the original production run over the whole observation (parent-file times). Identical to the file above in every field except `t_s` (offset 452.0 s) and `fit_s`. | AVX-512 cluster |
| `legacy38_avx512_disabled.jsonl` | Production env with AVX-512 disabled: `NPY_DISABLE_CPU_FEATURES="AVX512F AVX512CD AVX512_SKX"`, `OPENBLAS_CORETYPE=Haswell` ("M1") | AVX-512 cluster |
| `upstream_main_avx512.jsonl` | Production env, with burstfit from upstream main `6787f84` instead of 0.1.0 ("M2") | AVX-512 cluster |
| `legacy38_avx2.jsonl` | Production package versions rebuilt with uv (Python 3.8.20) | AVX2 machine |
| `v0.2.0_pipeline_py311_avx2.jsonl` | burstfit 0.2.0 wheel, Python 3.11, `constraints/pipeline.txt` (numpy 2.4.6, scipy 1.17.1, your 0.6.7) | AVX2 machine |

`fit_s` is wall time. It depends on machine load, so it is never compared, and fit times from runs that
shared a machine are not speed measurements.

## Method

- **Bit-identical comparison:** `compare.py new.jsonl [ref.jsonl]`. A row counts as identical only if every
  field matches exactly, NaN counting as equal to NaN; `fit_s` is ignored. Every result marked "50/50" below
  comes from this.
- **Statistics:** `summarize.py new.jsonl [ref.jsonl]` reports:
  - component-count changes;
  - the relative change in reduced χ²;
  - the brightest component's DM change in units of its error;
  - median DM and τ;
  - how many pulses use the same number of channels.
- **Data preparation only:** `maskcmp.py` fingerprints the spectral kurtosis, the RFI mask and the prepared
  spectrogram for each candidate, without fitting.
- **Fitting stage only:** `probe/fit_one.py` with `BF_PROBE=dump` saves the exact input BurstFit receives;
  `BF_PROBE=load` fits those saved inputs in another environment. The probe also has the runtime shims
  (`BF_SK_COMPAT`, `BF_NORM_COMPAT`) that 0.2.0 now provides as options.
- **Running:** `golden.sbatch` runs one environment on the golden set through Slurm and compares the result.
  Runs are single-threaded per fit (`OMP_NUM_THREADS=1`).

## Results

### 1. What changes the fits, with the code unchanged

Production env (burstfit 0.1.0, your 0.6.7, numpy 1.24.4, scipy 1.10.1) in every row:

| Run | vs | Identical |
|---|---|---|
| Golden chunk rerun, AVX-512 cluster (Xeon Gold 6126) | original production run (Xeon Gold 6138) | **50/50** (offset 452 s) |
| Same env again, AVX2 machine | itself | **50/50** |
| AVX-512 disabled, AVX-512 cluster (M1) | production | **0/50**; same channels used 50/50 |
| Rebuilt env, AVX2 machine (glibc 2.39) | production | **0/50** |
| Rebuilt env, AVX2 machine, inside a container with glibc 2.17 | M1 (AVX-512 disabled, glibc 2.17) | **50/50** |

On the same CPU, NumPy 1.24's float64 `exp`, `log` and `pow` give different bits under glibc 2.17 and 2.39.
So exact results depend on whether NumPy and OpenBLAS use AVX-512 code, and on glibc's libm. Masks and
channel counts never changed in these runs; only the fits did.

### 2. Python version

| Run | vs | Identical |
|---|---|---|
| burstfit 0.1.0, Python **3.11**, numpy 1.24.4, scipy 1.10.1 (AVX2 machine) | Python 3.8, same versions (AVX2 machine) | **50/50** |
| Same as above, Python 3.11, AVX-512 on (AVX-512 cluster) | production | **50/50** |
| Port branch, numpy 2.4.6, scipy 1.17.1, Python **3.14** (AVX2 machine) | Python **3.11**, same versions | **50/50** |
| burstfit 0.2.0 wheel, pipeline pins, Python 3.14 (AVX2 machine) | Python 3.11, same | **50/50** |

### 3. Data preparation: RFI masks and normalisation

**RFI masks.** In `your` 0.6.7, `sk_filter` sets its cutoff from the median and MAD of the spectral
kurtosis, which is a masked array. The masked (all-zero) channels' leftover values went into both
statistics up to SciPy 1.10. Newer SciPy leaves them out of the MAD only, so the cutoff depends on the
SciPy version. Results from `maskcmp.py` on the AVX2 machine, all compared with the Python 3.8 env:

| Env | RFI masks identical | Spectral kurtosis identical | Prepared spectrogram identical |
|---|---|---|---|
| Python 3.8 env with the legacy-cutoff shim (checks the shim) | 50/50 | 50/50 | 50/50 |
| numpy 2.4.6 / scipy 1.17.1, no shim | **0/50** (23–55 more channels flagged) | 14/50 | 0/50 |
| numpy 2.4.6 / scipy 1.17.1, legacy cutoff | **50/50** | 14/50 | 0/50 |
| numpy 2.5.5 / scipy 1.18.1, legacy cutoff | 50/50 | 14/50 | 0/50 |
| numpy 1.24.4 / scipy 1.10.1 on Python 3.11, legacy cutoff | 50/50 | 50/50 | 50/50 |

NumPy 2.x changes the spectral-kurtosis values in their last bits, but no channel crosses the cutoff. The
fixed cutoff (`your` branch `sk-filter-masked-mad`, default) uses only valid channels. It gave identical
fits with numpy 1.24.4/scipy 1.10.1 on Python 3.11 and numpy 2.2.6/scipy 1.14.1 on Python 3.13 (50/50).

**Normalisation.** `BurstData.normalise_data`, checked on `tests/data/28.fil`, one environment per NumPy
release on Python 3.11:

| numpy | Normalised spectrogram vs numpy 1.24.4 | Why |
|---|---|---|
| 1.25.2, 1.26.4 | identical | |
| 2.0.2, 2.1.3, 2.2.6 | float64 instead of float32; **identical once the data is kept float32** | NEP 50 promotes float32 minus a float64 scalar to float64 |
| 2.3.0, 2.3.5, 2.4.6 | differs even when kept float32 | float32 summation order changed in 2.3.0 (sum 22829352 vs 22829356) |

0.2.0 keeps the data's dtype by default.

### 4. Fitting stage (AVX2 machine, identical inputs)

burstfit 0.1.0 and the production wrapper fitted inputs saved from the 3.8 env (`BF_PROBE=load`), on Python
3.11 unless noted, compared with the 3.8 env's fits:

| numpy \ scipy | 1.10.1 | 1.11.4 | 1.12.0 | 1.13.1 | 1.14.1 | 1.15.0 | 1.15.3 | 1.16.3 | 1.17.1 |
|---|---|---|---|---|---|---|---|---|---|
| 1.24.4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ 0/50 | ✗ 0/50 | | |
| 1.25.2 | ✓ | | | | | | | | |
| 1.26.4 | ✓ | | | | | | | ✗ 0/50 | ✗ 0/50 |
| 2.0.2 / 2.1.3 / 2.2.6 | | | | | ✓ | | | | |
| 2.2.6 on Python 3.12 / 3.13 | | | | | ✓ | | | | |
| 2.4.6 on Python 3.14 | | | | | | | | | ✗ 0/50 |

✓ = 50/50 bit-identical. The numpy 1.24.4 / scipy 1.10.1 cell is a full-pipeline run on Python 3.11 (section
2), not a load-mode run. The cause of the SciPy break: SciPy 1.15.0 changed MINPACK `leastsq`, whose results
differ bit-wise from 1.14.1 on a test problem, while `least_squares(method="trf")` is identical. The
production wrapper's joint spectrogram fit is unbounded, so `curve_fit` uses `leastsq` for it. The bounded
profile and spectrum fits use TRF.

Full pipeline with the runtime shims, Python 3.13, numpy 2.2.6, scipy 1.14.1: 50/50 vs the 3.8 env; the same
run without the shims, 1/50.

### 5. AVX-512 (AVX-512 cluster, Xeon Gold 6138)

Full pipeline, burstfit 0.1.0 with both shims, AVX-512 on, vs production:

| Python | numpy | scipy | Identical |
|---|---|---|---|
| 3.11 | 1.24.4 | 1.10.1 | **50/50** |
| 3.11 | 1.24.4 | 1.14.1 | **50/50** |
| 3.11 | 1.25.2 | 1.14.1 | **50/50** |
| 3.11 | **1.26.4** | 1.14.1 | **50/50** |
| 3.11 | 2.0.2 | 1.14.1 | 0/50 |
| 3.11 | 2.1.3 | 1.14.1 | 0/50 |
| 3.13 | 2.2.6 | 1.14.1 | 0/50 |
| 3.13 | 2.2.6 | 1.14.1, AVX-512 disabled | **50/50 vs M1** |

NumPy 2.0 changed its AVX-512 float64 code paths. On machines without AVX-512, numpy up to 2.2.6 stays exact.
The NumPy 2.x runs agree closely with each other: 2.0.2 vs 2.1.3 was 49/50 counting NaN as equal, and the
remaining pulse differs only by one last bit in χ².

### 6. 0.2.0 exact-legacy mode, through the real options

The burstfit port branch and the `your` branch, with `validation/fit_one.py` and `BF_EXACT_LEGACY=1`, so
`spectral_kurtosis_legacy_mad=True` and `legacy_spectra_window=True`, without the runtime shims. Run on the
AVX2 machine and compared with the 3.8 env there:

| Python | numpy | scipy | Install | Identical |
|---|---|---|---|---|
| 3.13 | 2.2.6 | 1.14.1 | source tree | **50/50** |
| 3.11 | 1.24.4 | 1.14.1 | source tree | **50/50** |
| 3.12 | 1.26.4 | 1.14.1 | source tree | **50/50** |
| 3.12 | 1.26.4 | 1.14.1 | built 0.2.0 wheel and `your` wheel; tests 44/44 | **50/50** |
| 3.12 | 1.26.4 | 1.14.1 | built 0.2.0 wheel, through `golden.sbatch` | **50/50** |

Not yet run: the 0.2.0 wheel in exact-legacy mode on the AVX-512 cluster. Section 5 covers that combination
of versions, but with the shims rather than the options.

### 7. Statistical differences (no bit-identity)

Against production, over 49 pulses (t=7.634 left out):

| Run | Component count changed | Median rel. Δχ²r | Brightest-component DM: median \|Δ\|/σ, >3σ | Median DM | Median τ (ms) | Same channels used |
|---|---|---|---|---|---|---|
| production | – | – | – | 56.809 | 0.211 | – |
| M1: AVX-512 off (floating-point noise only) | 8 | 7.4e-4 | 0.92, 11 | 56.789 | 0.206 | 50/50 |
| 3.8 env, AVX2 machine (noise only) | 6 | 7.2e-4 | 0.68, 10 | 56.791 | 0.211 | 50/50 |
| M2: upstream main (`end+1` window) | 6 | 5.0e-4 | 0.81, 12 | 56.819 | 0.211 | 50/50 |
| 0.2.0 pipeline mode (numpy 2.4.6, scipy 1.17.1, your 0.6.7) | 11 | **2.7e-3** | 1.09, 18 | 56.836 | **0.219** | **1/50** |

The M1 and AVX2-machine rows show how much the fits move from floating-point noise alone. Main's window fix
(M2) can't be told apart from that noise with 50 pulses. 0.2.0's pipeline mode moves more, mostly because
`your` 0.6.7 flags different channels under SciPy ≥ 1.11 (section 3). Judging whether that is equivalent
needs the statistical test on all 2403 pulses (below).

**Fit time.** In production, one pulse (t=1.696) took 501 s of the 1065 s total; the median fit took 10 s.
With 38 workers, a 50-pulse run lasts about as long as its slowest fit. On the AVX-512 cluster, NumPy 2.x
runs took about 2 min against 9.5 min for NumPy 1.x. That difference is explained by NumPy 2.x avoiding that
pulse's long path, while NumPy 1.x reproduces it exactly. Single-core benchmarks on the AVX2 machine show the
same per-fit cost on numpy 1.24, 1.26, 2.0 and 2.2; per-fit cost was not benchmarked on AVX-512. Which fits
take a long path is itself chaotic.

## How to use exact-legacy mode

```bash
pip install -c constraints/exact-legacy.txt .   # Python 3.11-3.12; also needs a your with legacy_mad
```
```python
bd = BurstData(..., flag_rfi=True, spectral_kurtosis_legacy_mad=True)
bf = BurstFit(..., legacy_spectra_window=True)
```
`validation/fit_one.py` does this when `BF_EXACT_LEGACY=1`.

## Rerunning

```bash
cd validation
sbatch [site options] --export=ALL,PY=/path/to/env/bin/python,CHUNK=/path/to/chunk_452-461s.fil,MODE=exact golden.sbatch
```
- **Modes:** `pipeline` and `exact` (burstfit ≥ 0.2.0), `legacy` (burstfit 0.1.0 with the production wrapper)
  and `probe` (bisection).
- **Reference:** `REF=` chooses it; the default is production.
- **Comparing by hand:**
  ```bash
  python compare.py out.jsonl reference/legacy38_avx2.jsonl
  python summarize.py out.jsonl
  ```
- **Mask check:**
  ```bash
  python maskcmp.py chunk.fil a.json [--compat]
  python maskcmp.py --diff a.json b.json
  ```

Bit-identical comparisons need a reference made on the same kind of machine (AVX-512 or not, same glibc).
Use `production_avx512.jsonl` with AVX-512 and glibc 2.17, `legacy38_avx512_disabled.jsonl` with AVX-512
disabled and glibc 2.17, and `legacy38_avx2.jsonl` on an AVX2 machine with glibc 2.39.

## Next: statistical equivalence

From 0.2.0 on, changes are judged by statistical equivalence, not bit-identity. The plan is to compare the
distributions of the following against these references, on the full 2403-pulse B0355+54 set, with
thresholds agreed in advance:
- failure rate;
- component counts;
- reduced χ²;
- DM and τ.
