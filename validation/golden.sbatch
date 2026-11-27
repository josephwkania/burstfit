#!/bin/bash
#SBATCH -J bf-golden
#SBATCH -c 12
#SBATCH --mem=30G
#SBATCH -t 01:00:00
#SBATCH -o bf-golden-%j.out
# Fit the 50-pulse golden set once and compare it with a reference.
#
#   cd validation && sbatch [site options] golden.sbatch
# Environment (set with `sbatch --export=ALL,...` or export before submitting):
#   VALIDATION_DIR  this directory (default: the directory sbatch was run from)
#   PY        python of the environment under test (required)
#   CHUNK     path to chunk_452-461s.fil (required; checksum in golden/chunk_452-461s.fil.sha256)
#   MODE      pipeline (burstfit >= 0.2.0, default), exact (same, BF_EXACT_LEGACY=1),
#             legacy (burstfit 0.1.0's production wrapper) or probe (see probe/fit_one.py)
#   REF       reference to compare against (default reference/production_avx512.jsonl)
#   WORK      output directory (default ./golden_<jobid>)
set -euo pipefail
V=${VALIDATION_DIR:-$SLURM_SUBMIT_DIR}
[ -f "$V/run_batch.py" ] || { echo "VALIDATION_DIR ($V) is not the validation directory" >&2; exit 2; }
: "${PY:?set PY}" "${CHUNK:?set CHUNK}"
MODE=${MODE:-pipeline}
REF=${REF:-$V/reference/production_avx512.jsonl}
WORK=${WORK:-$PWD/golden_${SLURM_JOB_ID}}
mkdir -p "$WORK/plots" "$WORK/stage"; cd "$WORK"
# Stage the chunk on node-local storage if there is room; small parallel reads are slow on shared filesystems.
STAGE=${TMPDIR:-/tmp}/bf_golden_$SLURM_JOB_ID; mkdir -p "$STAGE"; cp "$CHUNK" "$STAGE/"
trap 'rm -rf "$STAGE"' EXIT
(cd "$STAGE" && sha256sum -c "$V/golden/chunk_452-461s.fil.sha256")
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MPLBACKEND=Agg PYTHONWARNINGS=ignore
export BF_IN=$V/golden/batch_chunk.csv BF_OUT=$WORK/out.jsonl BF_STAGE=$STAGE
case $MODE in
  pipeline) export BF_FIT_DIR=$V BF_EXACT_LEGACY=0 ;;
  exact)    export BF_FIT_DIR=$V BF_EXACT_LEGACY=1 ;;
  legacy)   export BF_FIT_DIR=$V/legacy ;;
  probe)    export BF_FIT_DIR=$V/probe ;;
  *) echo "unknown MODE $MODE" >&2; exit 2 ;;
esac
"$PY" -c "import sys; sys.path.insert(0, '$BF_FIT_DIR'); import fit_one, burstfit, your, numpy, scipy, platform; print(platform.node(), sys.version.split()[0], 'numpy', numpy.__version__, 'scipy', scipy.__version__, 'burstfit', burstfit.__version__, burstfit.__file__, 'your', your.__version__, 'mode $MODE')" | tee which.txt
grep -m1 "model name" /proc/cpuinfo | tee -a which.txt
"$PY" "$V/run_batch.py" "$SLURM_CPUS_PER_TASK"
"$PY" "$V/compare.py" "$WORK/out.jsonl" "$REF" | tee compare.txt | sed -n 3,4p
