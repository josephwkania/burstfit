"""Per-candidate fingerprints of the data preparation (spectral kurtosis, RFI mask, prepared spectrogram) for
the golden set, to compare environments without fitting.

usage: python maskcmp.py <chunk.fil> <out.json> [--compat]
  --compat: replace your.utils.rfi.sk_filter with a copy that reproduces SciPy <= 1.10's
            median_abs_deviation (masked channels' values included), as your 0.6.7 got on the 3.8 stack.
Compare two outputs with:  python maskcmp.py --diff <a.json> <b.json>
"""
import csv, hashlib, json, logging, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
H = lambda a: hashlib.sha256(np.ascontiguousarray(np.ma.getdata(a)).tobytes()).hexdigest()[:16]

if sys.argv[1] == "--diff":
    a, b = (json.load(open(p)) for p in sys.argv[2:4])
    for k in ("sk", "mask", "sgram"):
        print(f"{k:6s} identical {sum(a[t][k] == b[t][k] for t in a)}/{len(a)}")
    dn = [b[t]["nflag"] - a[t]["nflag"] for t in a]
    print(f"flagged fine channels, b - a: min {min(dn)}, max {max(dn)}")
    sys.exit()

logging.disable(logging.WARNING)
import your.utils.rfi as rfi
from burstfit.data import BurstData

REC = {}
_sk_orig = rfi.spectral_kurtosis
def _sk_spy(*a, **k):
    sk = _sk_orig(*a, **k)
    REC["sk"] = H(sk)
    return sk
rfi.spectral_kurtosis = _sk_spy


def sk_filter_legacy(data, channel_bandwidth, tsamp, N=None, d=None, sigma=5):
    """your 0.6.7 sk_filter with the MAD written out as SciPy <= 1.10 computed it."""
    if not N:
        N = rfi.calc_N(channel_bandwidth, tsamp)
    sk = rfi.spectral_kurtosis(data, d=d, N=N)
    nan_mask = np.isnan(sk)
    sk[nan_mask] = np.nan
    sk_c = sk[~nan_mask]
    x = np.asarray(sk_c)  # SciPy <= 1.10: asarray drops the mask
    std = 1.4826 * (np.median(np.abs(x - np.expand_dims(np.median(x, axis=0), 0)), axis=0) / 1.0)
    h = np.median(sk_c) + sigma * std
    l = np.median(sk_c) - sigma * std
    mask = (sk < h) & (sk > l)
    return ~mask


if "--compat" in sys.argv:
    rfi.sk_filter = sk_filter_legacy

chunk, out_p = sys.argv[1], sys.argv[2]
out = {}
for r in csv.DictReader(open(os.path.join(HERE, "golden", "batch_chunk.csv"))):
    REC.clear()
    bd = BurstData(fp=chunk, dm=float(r["dm"]), tcand=float(r["t"]), width=max(1, int(float(r["width"]))),
                   snr=float(r["snr"]), flag_rfi=True)
    bd.prepare_data(time_window=0.1)
    m = np.asarray(bd.mask)
    out[r["t"]] = dict(REC, mask=H(m), nflag=int(m.sum()), sgram=H(bd.sgram))
json.dump(out, open(out_p, "w"), indent=0)
print(len(out), "candidates; median flagged", int(np.median([v["nflag"] for v in out.values()])))
