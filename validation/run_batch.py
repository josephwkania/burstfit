"""Fit every row of a batch CSV with fit_one.fit, in parallel. -> JSON lines (one per candidate, or its error).

usage: python run_batch.py [nworkers]
  BF_IN       input CSV (columns fil,t,dm,width,snr,on), default batch.csv
  BF_OUT      output JSON-lines file, default results.jsonl
  BF_STAGE    directory holding the .fil files (replaces each row's directory)
  BF_FIT_DIR  directory of the fit_one.py to use, default: this directory. Python puts a script's own
              directory first on sys.path, ahead of PYTHONPATH, so choose the variant here:
              validation/ (burstfit >= 0.2.0), validation/legacy/ (burstfit 0.1.0) or validation/probe/.

Same as the production runner used for the B0355+54 test, except for BF_FIT_DIR and the docstring.
Plots for the 20 highest-S/N rows and every 50th row go to ./plots.
"""
import csv, json, os, sys, time, traceback
from multiprocessing import Pool
os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, os.environ.get("BF_FIT_DIR", os.path.dirname(os.path.abspath(__file__))))
import fit_one
rows = sorted(csv.DictReader(open(os.environ.get("BF_IN", "batch.csv"))), key=lambda r: (r["fil"], float(r["t"])))  # sequential reads
if os.environ.get("BF_STAGE"):
    for r in rows:
        r["fil"] = os.path.join(os.environ["BF_STAGE"], os.path.basename(r["fil"]))
plot_ids = set(sorted(range(len(rows)), key=lambda i: -float(rows[i]["snr"]))[:20]) | set(range(0, len(rows), 50))
def one(i):
    r = rows[i]
    try:
        out = fit_one.fit(r["fil"], float(r["t"]), float(r["dm"]), float(r["width"]), float(r["snr"]),
                          "plots" if i in plot_ids else None)
    except Exception as e:
        out = {"fil": os.path.basename(r["fil"]), "tcand": float(r["t"]), "dm_in": float(r["dm"]),
               "snr_in": float(r["snr"]), "error": f"{type(e).__name__}: {str(e)[:200]}"}
    out["on"] = int(r["on"]); out["i"] = i
    return out
if __name__ == "__main__":
    t0 = time.time(); n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    with open(os.environ.get("BF_OUT", "results.jsonl"), "w") as f, Pool(n) as p:
        for k, out in enumerate(p.imap_unordered(one, range(len(rows)), chunksize=8)):
            f.write(json.dumps(out, default=float) + "\n"); f.flush()
            if k % 200 == 0: print(f"{k}/{len(rows)} {time.time() - t0:.0f} s", flush=True)
    print(f"done {len(rows)} in {time.time() - t0:.0f} s")
