"""Fit one single-pulse candidate with BurstFit (Aggarwal et al. 2021): a Gaussian convolved with a scattering
tail (tau scales as nu^-4), a Gaussian spectrum, and the DM, fitted to the dedispersed dynamic spectrum.
usage: fit_one.py <fil> <tcand s> <dm> <width samples> <snr> [outdir] [fdecim]   -> one JSON line on stdout"""
import json, logging, sys, time, os
import numpy as np
logging.disable(logging.WARNING)
from burstfit.data import BurstData
from burstfit.fit import BurstFit
from burstfit.model import Model, SgramModel
from burstfit.utils.functions import pulse_fn_vec, gauss_norm, sgram_fn_vec
import burstfit.curvefit as _cf

# BurstFit 0.1.0 calls curve_fit without a starting point for the profile and spectrum fits, so it starts at the
# middle of the bounds and often runs out of evaluations. Start from the data instead: the peak and its position.
_cf_orig = _cf.CurveFit.cf
def _cf_with_p0(self):
    if self.p0 is None and np.ndim(self.bounds) == 2 and len(self.bounds[0]) in (2, 4):
        lo, hi = np.asarray(self.bounds[0], float), np.asarray(self.bounds[1], float)
        y = np.asarray(self.ydata); x = np.asarray(self.xdata); k = int(np.argmax(y))
        if len(lo) == 4:                                  # pulse: S, mu, sigma, tau
            p0 = [max(y[k], 1e-3) * 3, x[k], 2.0, 1.0]
        else:                                             # Gaussian spectrum: mu, sigma
            p0 = [x[k], max(len(x) / 4, 1.0)]
        span = hi - lo
        eps = np.where(np.isfinite(span), 1e-6 * span, 1e-6)
        self.p0 = list(np.clip(p0, lo + eps, hi - eps))
    # curve_fit's default budget (100 x (n+1) evaluations) is too small for the joint fits of 2-3 components
    from scipy.optimize import curve_fit
    unbounded = np.all(np.isinf(np.asarray(self.bounds, float)))   # curve_fit then uses leastsq, which spells it maxfev
    budget = {"maxfev": MAX_NFEV} if unbounded else {"max_nfev": MAX_NFEV}
    popt, pcov = curve_fit(self.function, xdata=self.xdata, ydata=self.ydata, p0=self.p0, bounds=self.bounds,
                           **budget)
    return popt, np.sqrt(np.diag(pcov))
MAX_NFEV = 5000
_cf.CurveFit.cf = _cf_with_p0

def decimate(bd, k, max_bad=0.5):
    """Average k adjacent (dedispersed) channels, using only the unflagged ones; a coarse channel is masked only
    when more than MAX_BAD of its k are flagged (masking it for any one flag threw away ~15% more of the band)."""
    nt, nf = bd.sgram.shape[1], bd.sgram.shape[0]
    m = bd.mask.copy(); s = np.ma.array(np.ma.getdata(bd.sgram), mask=np.repeat(m[:, None], nt, 1))
    s = s.reshape(nf // k, k, nt).mean(1)
    mk = m.reshape(nf // k, k).mean(1) > max_bad
    s = np.ma.filled(s, 0).astype(np.float64)
    # Per-channel baseline and noise from the window's outer 30% on each side (the raw files' bandpass is not
    # flat, and BurstData's normalisation is one mean and std for the whole band).
    e = int(0.3 * nt); off = np.concatenate([s[:, :e], s[:, -e:]], 1)
    med = np.median(off, 1); sd = 1.4826 * np.median(np.abs(off - med[:, None]), 1)
    mk |= ~(sd > 0)
    s = np.where(mk[:, None], 0, (s - med[:, None]) / np.where(sd > 0, sd, 1)[:, None])
    return np.ma.array(s, mask=np.repeat(mk[:, None], nt, 1)), mk

def fit(fil, tcand, dm, width, snr, outdir=None, k=8, twin=0.1, max_ncomp=3):
    """Fit with up to MAX_NCOMP components; if that fit fails to converge, retry with fewer."""
    t0, err = time.time(), None
    for n in range(max_ncomp, 0, -1):
        try:
            out = _fit(fil, tcand, dm, width, snr, outdir, k, twin, n)
            out.update(max_ncomp_tried=max_ncomp, max_ncomp_used=n, fit_s=round(time.time() - t0, 1))
            return out
        except (RuntimeError, AssertionError, ValueError) as e:
            err = e
    raise err

def _fit(fil, tcand, dm, width, snr, outdir, k, twin, max_ncomp):
    t0 = time.time()
    bd = BurstData(fp=fil, dm=dm, tcand=tcand, width=max(1, int(width)), snr=snr, flag_rfi=True)
    bd.prepare_data(time_window=twin)
    sgram, mask = decimate(bd, k) if k > 1 else (bd.sgram, bd.mask)
    foff = bd.foff * k
    fch1 = bd.fch1 + (k - 1) / 2 * bd.foff          # centre of the first averaged channel
    pulse = Model(pulse_fn_vec, param_names=["S", "mu_t", "sigma_t", "tau"])
    spectra = Model(gauss_norm, param_names=["mu_f", "sigma_f"])
    sm = SgramModel(pulse, spectra, sgram_fn_vec, mask=mask, clip_fac=np.inf)   # no 8-bit clipping after our normalisation
    bf = BurstFit(sgram_model=sm, sgram=sgram, width=bd.width, dm=dm, foff=foff, fch1=fch1,
                  tsamp=bd.tsamp, clip_fac=np.inf, mask=mask)
    bf.validate(); bf.precalc()
    bf.fitall(plot=False, max_ncomp=max_ncomp)
    names = bf.param_names
    comps = []
    for c, v in bf.sgram_params["all"].items():
        p = dict(zip(names, v["popt"])); e = dict(zip(names, v["perr"]))
        comps.append({
            "fluence_au": p["S"],
            "t_s": tcand + (p["mu_t"] - bf.nt / 2) * bd.tsamp, "t_err_ms": e["mu_t"] * bd.tsamp * 1e3,
            "width_ms": p["sigma_t"] * bd.tsamp * 1e3, "width_err_ms": e["sigma_t"] * bd.tsamp * 1e3,
            "fwhm_ms": 2.3548 * p["sigma_t"] * bd.tsamp * 1e3,
            "tau_ms": p["tau"] * bd.tsamp * 1e3, "tau_err_ms": e["tau"] * bd.tsamp * 1e3,
            "tau_ref_mhz": fch1,                                  # tau is at the top of the band
            "spec_peak_mhz": fch1 + p["mu_f"] * foff, "spec_sigma_mhz": abs(p["sigma_f"] * foff),
            "dm": p["DM"], "dm_err": e["DM"]})
    out = {"fil": os.path.basename(fil), "tcand": tcand, "dm_in": dm, "width_in": width, "snr_in": snr,
           "ncomp": bf.ncomponents, "redchisq": float(bf.reduced_chi_sq), "nchan_used": int((~mask).sum()),
           "nchan": int(mask.size), "fit_s": round(time.time() - t0, 1), "components": comps}
    if outdir:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        mdl = bf.model
        fig, ax = plt.subplots(1, 4, figsize=(14, 3.5))
        sg = np.ma.filled(sgram, np.nan); lim = np.nanpercentile(sg[~mask], [1, 99])
        for a, d, t in zip(ax[:3], (sg, mdl, sg - mdl), ("data", "model", "residual")):
            a.imshow(np.where(mask[:, None], np.nan, d), aspect="auto", vmin=lim[0], vmax=lim[1], cmap="viridis",
                     extent=[0, sgram.shape[1] * bd.tsamp * 1e3, fch1 + foff * sgram.shape[0], fch1]); a.set_title(t)
            a.set_xlabel("ms")
        ax[0].set_ylabel("MHz")
        tt = np.arange(sgram.shape[1]) * bd.tsamp * 1e3
        ax[3].plot(tt, sg[~mask].sum(0), "k", lw=0.8, label="data"); ax[3].plot(tt, mdl[~mask].sum(0), "r", lw=1, label="model")
        ax[3].legend(fontsize=7); ax[3].set_xlabel("ms")
        c = comps[0]
        fig.suptitle(f"{os.path.basename(fil)} t={tcand:.3f}s  DM {c['dm']:.2f}±{c['dm_err']:.2f}  FWHM {c['fwhm_ms']:.2f} ms  "
                     f"tau {c['tau_ms']:.3f}±{c['tau_err_ms']:.3f} ms  ncomp {bf.ncomponents}  chi2r {out['redchisq']:.2f}", fontsize=9)
        fig.tight_layout(); os.makedirs(outdir, exist_ok=True)
        fig.savefig(f"{outdir}/{os.path.basename(fil)[:-4]}_t{tcand:.3f}.png", dpi=80); plt.close(fig)
    return out

if __name__ == "__main__":
    a = sys.argv
    print(json.dumps(fit(a[1], float(a[2]), float(a[3]), float(a[4]), float(a[5]),
                         a[6] if len(a) > 6 else None, int(a[7]) if len(a) > 7 else 8), default=float))
