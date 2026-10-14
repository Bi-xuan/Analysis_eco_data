# Analysis_eco_data

Run Lambda support recovery on the covariance exported by `analyze_data.ipynb`:

```bash
python run_lambda_support_recovery.py --n-jobs 20
```

Use an environment with the packages in `requirements.txt` installed (Python
3.10+). The default input is
`Dataset/rodent_flea/top_10_empirical_covariance_mle.pkl`, with 48 observations,
upper-triangle greedy nested search, fitted omega, and plateau-bootstrap
selection. Configure another matrix with `--input PATH --num-samples N`;
the sample count must match the observations used to compute that matrix.
Run `python run_lambda_support_recovery.py --help` for fitting and bootstrap options.
The pinned package supports `plateau-bootstrap` and `plateau` selection.

Each run creates a separate directory under
`experiments/output/lambda_support_recovery` (configurable with `--output-root`):

- `result.pkl`: complete package `SelectionResult`, including diagnostics.
- `support.pkl`: Boolean support DataFrame with species labels and diagonals.
- `fitted_lambda.pkl`: fitted Lambda DataFrame with species labels.
- `curve.pkl`: fitted curve from the successful result, available for later reselection.
- `summary.json`: settings, package versions, selected edges, omega, and run status.

Reload the labeled support with `pd.read_pickle("RUN_DIRECTORY/support.pkl")`.
Reloading the complete result or curve also requires `lambda-support-recovery`.
Failed runs exit with an error and record it in `summary.json`; no alternative
selection method is substituted.
The runner calls `select_support(..., return_result=True)`. If that call fails,
the package does not return its curve, so the failed run contains its summary only.

Submit on the SGE cluster from this project root, after activating your Python
environment and ensuring the log directory exists:

```bash
mkdir -p experiments/output
qsub experiments/submit_lambda_support_recovery.sh
```

The script requests 20 CPUs on `long.q`, passes `NSLOTS` to the package's
`n_jobs`, and limits BLAS to one thread per worker. It uses the submitted
environment's Python; override it with `PYTHON_BIN` if necessary. For example:

```bash
INPUT_COVARIANCE=Dataset/rodent_flea/another_covariance.pkl NUM_SAMPLES=100 \
OUTPUT_ROOT=experiments/output/another_dataset \
qsub experiments/submit_lambda_support_recovery.sh
```

Other environment overrides include `METHOD`, `SUPPORT_SCOPE`, `MAX_RESTARTS`,
`MAX_ITER`, and `BOOTSTRAP_REPLICATES`. For known omega, set
`FIT_OMEGA_REF=false OMEGA_REF=VALUE`; otherwise leave their defaults unchanged.
