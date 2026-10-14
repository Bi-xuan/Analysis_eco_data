#!/bin/bash
#$ -q long.q
#$ -cwd
#$ -V
#$ -pe thread 20
#$ -j y
#$ -o experiments/output
#$ -M liubixuan214@gmail.com
#$ -m ea

set -euo pipefail

cd "${SGE_O_WORKDIR:?Submit with qsub from the Analysis_eco_data project root}"
if [[ ! -f run_lambda_support_recovery.py ]]; then
    echo "Error: submit this script from the Analysis_eco_data project root." >&2
    exit 1
fi

INPUT_COVARIANCE="${INPUT_COVARIANCE:-Dataset/rodent_flea/top_10_empirical_covariance_mle.pkl}"
NUM_SAMPLES="${NUM_SAMPLES:-48}"
METHOD="${METHOD:-plateau-bootstrap}"
SUPPORT_SCOPE="${SUPPORT_SCOPE:-upper}"
OMEGA_REF="${OMEGA_REF:-none}"
FIT_OMEGA_REF="${FIT_OMEGA_REF:-true}"
OUTPUT_ROOT="${OUTPUT_ROOT:-experiments/output/lambda_support_recovery}"
PYTHON_BIN="${PYTHON_BIN:-python}"
MAX_RESTARTS="${MAX_RESTARTS:-10}"
MAX_ITER="${MAX_ITER:-800}"
BOOTSTRAP_REPLICATES="${BOOTSTRAP_REPLICATES:-199}"

export TOTAL_CPUS="${NSLOTS:-20}"
# The package uses worker processes; keep numerical libraries to one thread each.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export BLIS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTHONUNBUFFERED=1

omega_args=()
case "${FIT_OMEGA_REF}" in
    true) omega_args+=(--fit-omega-ref) ;;
    false) omega_args+=(--no-fit-omega-ref) ;;
    *) echo "Error: FIT_OMEGA_REF must be true or false." >&2; exit 1 ;;
esac
if [[ "${OMEGA_REF}" != none ]]; then
    omega_args+=(--omega-ref "${OMEGA_REF}")
fi

echo "Conda environment: ${CONDA_DEFAULT_ENV:-unset}"
"${PYTHON_BIN}" -c 'import sys; print("Python:", sys.executable)'
echo "Allocated CPUs: ${TOTAL_CPUS}"

"${PYTHON_BIN}" run_lambda_support_recovery.py \
    --input "${INPUT_COVARIANCE}" \
    --num-samples "${NUM_SAMPLES}" \
    --output-root "${OUTPUT_ROOT}" \
    --n-jobs "${TOTAL_CPUS}" \
    --method "${METHOD}" \
    --support-scope "${SUPPORT_SCOPE}" \
    --max-restarts "${MAX_RESTARTS}" \
    --max-iter "${MAX_ITER}" \
    --bootstrap-replicates "${BOOTSTRAP_REPLICATES}" \
    "${omega_args[@]}" "$@"
