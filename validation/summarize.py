"""Compact summary of a golden-set run vs a reference: per-pulse redchisq / ncomp / DM / tau changes.

usage: python summarize.py <new.jsonl> [ref.jsonl]
  ref defaults to reference/production_avx512.jsonl.
Pulses whose reference fit is degenerate (NaN chi-squared, or brightest-first-component DM more than 20 from
B0355+54's 57.1) are excluded from the statistics.

Originally written for the baseline export; the reference path became an argument here.
"""
import json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ref_p = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "reference", "production_avx512.jsonl")
R = {round(json.loads(l)["tcand"], 4): json.loads(l) for l in open(ref_p)}
N = {round(json.loads(l)["tcand"], 4): json.loads(l) for l in open(sys.argv[1])}
finite = lambda x: x == x
bad = [t for t in R if not finite(R[t]["redchisq"]) or abs(R[t]["components"][0]["dm"] - 57.1) > 20]
print("excluded (reference fit degenerate: NaN chi2 or |DM-57.1|>20):", bad)
ts = [t for t in R if t not in bad]
rel = sorted(abs(N[t]["redchisq"] - R[t]["redchisq"]) / R[t]["redchisq"] for t in ts if finite(N[t]["redchisq"]))
print(f"pulses {len(ts)}; ncomp changed {sum(N[t]['ncomp'] != R[t]['ncomp'] for t in ts)}")
print(f"|d redchisq|/redchisq: <1e-8 in {sum(r < 1e-8 for r in rel)}, <1e-4 in {sum(r < 1e-4 for r in rel)}, "
      f"median {st.median(rel):.1e}, max {max(rel):.1e}")
dn = [N[t]["redchisq"] - R[t]["redchisq"] for t in ts if finite(N[t]["redchisq"])]
print(f"new chi2 lower in {sum(d < 0 for d in dn)}, higher in {sum(d > 0 for d in dn)}; median redchisq ref "
      f"{st.median(R[t]['redchisq'] for t in ts):.5f} new {st.median(N[t]['redchisq'] for t in ts if finite(N[t]['redchisq'])):.5f}")
def bright(r):  # the brightest component
    return max(r["components"], key=lambda c: c["fluence_au"])
d = [(bright(N[t])["dm"] - bright(R[t])["dm"]) / bright(R[t])["dm_err"] for t in ts]
print(f"brightest-component DM change / its error: median|.| {st.median(map(abs, d)):.2f}, >1 sigma in {sum(abs(x) > 1 for x in d)}, >3 sigma in {sum(abs(x) > 3 for x in d)}")
print(f"median brightest-comp DM: ref {st.median(bright(R[t])['dm'] for t in ts):.4f} new {st.median(bright(N[t])['dm'] for t in ts):.4f}")
print(f"median brightest-comp tau_ms: ref {st.median(bright(R[t])['tau_ms'] for t in ts):.4f} new {st.median(bright(N[t])['tau_ms'] for t in ts):.4f}")
print(f"nchan_used identical in {sum(N[t]['nchan_used'] == R[t]['nchan_used'] for t in R)}/{len(R)}")
one = [t for t in ts if R[t]["ncomp"] == 1 and N[t]["ncomp"] == 1]
print("1-component pulses, rel d chi2:", ", ".join(f"{abs(N[t]['redchisq']-R[t]['redchisq'])/R[t]['redchisq']:.0e}" for t in sorted(one)))
print("sum fit_s ref %.0f new %.0f" % (sum(R[t]["fit_s"] for t in R), sum(N[t]["fit_s"] for t in R)))
