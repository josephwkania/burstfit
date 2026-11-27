"""Probe wrapper around legacy/fit_one.py, the production wrapper used with burstfit 0.1.0. Select it with
BF_FIT_DIR=<this directory> for run_batch.py, and put burstfit 0.1.0 first on PYTHONPATH.

BF_PROBE=dump  save each candidate's decimated, normalised input (what BurstFit is given) to BF_PROBE_DIR
BF_PROBE=load  fit from those saved inputs instead of preparing the data, so only the fitting stage differs
BF_PROBE=off   plain production behaviour
BF_SK_COMPAT=1   use the SciPy <= 1.10 MAD behaviour in your's sk_filter (masked values included)
BF_NORM_COMPAT=1 keep BurstData's normalised spectrogram float32 under NumPy 2, as NumPy 1.x did

These shims patch your 0.6.7 and burstfit 0.1.0 at runtime. They were used for the bisection in
VALIDATION.md; burstfit >= 0.2.0 has the same behaviour as real options (see validation/fit_one.py).
"""
import os
import numpy as np

if not hasattr(np, "trapz"):  # burstfit 0.1.0 calls np.trapz (removed in NumPy 2); scipy's is bit-identical
    from scipy.integrate import trapezoid as _trapezoid
    np.trapz = _trapezoid

if os.environ.get("BF_SK_COMPAT") == "1":
    import your.utils.rfi as _rfi

    def _sk_filter_legacy(data, channel_bandwidth, tsamp, N=None, d=None, sigma=5):
        if not N:
            N = _rfi.calc_N(channel_bandwidth, tsamp)
        sk = _rfi.spectral_kurtosis(data, d=d, N=N)
        nan_mask = np.isnan(sk)
        sk[nan_mask] = np.nan
        sk_c = sk[~nan_mask]
        x = np.asarray(sk_c)  # SciPy <= 1.10's median_abs_deviation dropped the mask
        std = 1.4826 * (np.median(np.abs(x - np.expand_dims(np.median(x, axis=0), 0)), axis=0) / 1.0)
        h = np.median(sk_c) + sigma * std
        l = np.median(sk_c) - sigma * std
        mask = (sk < h) & (sk > l)
        return ~mask

    _rfi.sk_filter = _sk_filter_legacy

if os.environ.get("BF_NORM_COMPAT") == "1":
    # NumPy 1.x value-based casting: float32 array - float64 scalar stayed float32. NumPy 2 (NEP 50) promotes
    # to float64. Cast the scalars to the data's dtype so the normalised spectrogram is float32 as before.
    import burstfit.data as _bdata

    def _normalise_data_legacy(self, on_pulse_data, off_pulse_data, return_clip_fac=True):
        off_pulse_mean = np.mean(off_pulse_data)
        off_pulse_std = np.std(off_pulse_data)
        dt = on_pulse_data.dtype.type
        on_pulse_data = on_pulse_data - dt(off_pulse_mean)
        on_pulse_data = on_pulse_data / dt(off_pulse_std)
        if return_clip_fac:
            clip_fac = ((2 ** self.nbits - 1) - off_pulse_mean) / off_pulse_std
            return on_pulse_data, clip_fac
        return on_pulse_data

    _bdata.BurstData.normalise_data = _normalise_data_legacy

_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "legacy", "fit_one.py")
exec(compile(open(_src).read(), _src, "exec"))

_decimate = globals()["decimate"]  # defined by the exec above
_MODE = os.environ.get("BF_PROBE", "off")
_DIR = os.environ.get("BF_PROBE_DIR", "")


def decimate(bd, k, max_bad=0.5):
    if _MODE == "off":
        return _decimate(bd, k, max_bad)
    f = f"{_DIR}/{bd.tcand:.4f}_k{k}.npz"
    if _MODE == "dump":
        s, mk = _decimate(bd, k, max_bad)
        np.savez(f, data=np.ma.getdata(s), mask=np.ma.getmaskarray(s), mk=mk)
        return s, mk
    z = np.load(f)
    return np.ma.array(z["data"], mask=z["mask"]), z["mk"]
