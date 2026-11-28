"""Compare a run_batch.py output on the golden set with a reference, field by field.

usage: python compare.py <new.jsonl> [ref.jsonl] [offset_s]
  ref defaults to reference/production_avx512.jsonl (chunk times, the same as new), offset 0.
  For reference/production_orig_rows.jsonl (parent-file times) pass offset 452.0.

Rows are matched on tcand (+offset). fit_s (wall time), i and fil are ignored. t_s is compared after removing
the offset (within 1e-9 s when offset != 0, since adding 452.0 is not exact in floating point). Everything
else must be exactly equal for a row to count as bit-identical; NaN counts as equal to NaN (some fits end
with NaN reduced chi-squared, and they are reproducible as such).

Originally written for the baseline export; the NaN handling and default paths were added here.
"""
import json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
new_p = sys.argv[1]
ref_p = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "reference", "production_avx512.jsonl")
off = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
IGNORE = {"fit_s", "i", "fil"}


def load(p):
    return {round(json.loads(l)["tcand"], 4): json.loads(l) for l in open(p) if l.strip()}


def flat(r, off):
    d = {k: v for k, v in r.items() if k not in IGNORE and k != "components"}
    d["tcand"] = round(r["tcand"] - off, 6)
    for j, c in enumerate(r.get("components", [])):
        for k, v in c.items():
            d[f"c{j}.{k}"] = v - off if k == "t_s" else v
    return d


def equal(x, y):
    if isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y):
        return True
    return x == y


ref, new = load(ref_p), load(new_p)
same, diffs, missing = 0, [], []
for t, r in sorted(ref.items()):
    n = new.get(round(t - off, 4)) if off else new.get(t)
    if n is None:
        missing.append(t); continue
    a, b = flat(r, off), flat(n, 0.0)
    bad = []
    for k in sorted(set(a) | set(b)):
        x, y = a.get(k), b.get(k)
        if k.endswith("t_s") and off and isinstance(x, float) and isinstance(y, float):
            ok = abs(x - y) < 1e-9
        else:
            ok = equal(x, y)
        if not ok:
            bad.append(k)
    if not bad:
        same += 1; continue
    row = {"tcand": t, "ncomp_ref": r.get("ncomp"), "ncomp_new": n.get("ncomp"), "nfields": len(bad),
           "nchan_used": (r.get("nchan_used"), n.get("nchan_used")),
           "d_redchisq": (n.get("redchisq") or float("nan")) - (r.get("redchisq") or float("nan")),
           "error": (r.get("error"), n.get("error"))}
    if r.get("ncomp") == n.get("ncomp") and r.get("components"):
        comp = []
        for cr, cn in zip(r["components"], n["components"]):
            comp.append({
                "dDM": cn["dm"] - cr["dm"], "dDM/err": (cn["dm"] - cr["dm"]) / cr["dm_err"] if cr["dm_err"] else None,
                "dtau_ms": cn["tau_ms"] - cr["tau_ms"],
                "dtau/err": (cn["tau_ms"] - cr["tau_ms"]) / cr["tau_err_ms"] if cr["tau_err_ms"] else None})
        row["components"] = comp
    diffs.append(row)

print(f"ref {ref_p}\nnew {new_p}\n{same} / {len(ref)} bit-identical (fit_s ignored); "
      f"{len(diffs)} differ; {len(missing)} missing from new")
nc = sum(d["ncomp_ref"] != d["ncomp_new"] for d in diffs)
print(f"ncomp changed in {nc} of the differing rows")
for d in diffs:
    s = (f"t={d['tcand']:.3f} ncomp {d['ncomp_ref']}->{d['ncomp_new']} nchan_used {d['nchan_used'][0]}->{d['nchan_used'][1]} "
         f"d_redchisq={d['d_redchisq']:+.3e} fields_differ={d['nfields']}")
    if d["error"] != (None, None):
        s += f" error={d['error']}"
    print(s)
    for j, c in enumerate(d.get("components", [])):
        f = lambda v: "n/a" if v is None else f"{v:+.2f}"
        print(f"    c{j}: dDM={c['dDM']:+.4g} ({f(c['dDM/err'])} sigma)  dtau={c['dtau_ms']:+.4g} ms ({f(c['dtau/err'])} sigma)")
if diffs:
    import statistics as st
    dd = [abs(c["dDM/err"]) for d in diffs for c in d.get("components", []) if c["dDM/err"] is not None]
    dt = [abs(c["dtau/err"]) for d in diffs for c in d.get("components", []) if c["dtau/err"] is not None]
    if dd:
        print(f"|dDM|/err over components with same ncomp: median {st.median(dd):.3g}, max {max(dd):.3g}")
    if dt:
        print(f"|dtau|/err: median {st.median(dt):.3g}, max {max(dt):.3g}")
    print("|d_redchisq|: max %.3e" % max(abs(d["d_redchisq"]) for d in diffs))
