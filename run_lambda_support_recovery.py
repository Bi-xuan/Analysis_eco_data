"""Recover Lambda support from a configurable pickled covariance matrix."""

from __future__ import annotations

import argparse
import json
from importlib.metadata import version
from pathlib import Path
import tempfile

import numpy as np
import pandas as pd

from lambda_support_recovery import select_support


def integer_at_least(minimum: int):
    def parse(value: str) -> int:
        number = int(value)
        if number < minimum:
            raise argparse.ArgumentTypeError(f"Must be at least {minimum}.")
        return number

    return parse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=Path("Dataset/rodent_flea/top_10_empirical_covariance_mle.pkl"),
        help="Pickled pandas covariance DataFrame.",
    )
    parser.add_argument(
        "--num-samples", type=integer_at_least(2), default=48,
        help="Number of observations used to estimate the covariance (not its dimension).",
    )
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("experiments/output/lambda_support_recovery"),
        help="A unique run directory is created here for each invocation.",
    )
    parser.add_argument("--n-jobs", type=integer_at_least(1), default=1)
    parser.add_argument("--method", choices=("plateau-bootstrap", "plateau"), default="plateau-bootstrap")
    parser.add_argument("--support-scope", choices=("upper", "all"), default="upper")
    parser.add_argument("--omega-ref", type=float, default=None)
    parser.add_argument("--fit-omega-ref", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--kappa", type=float, default=0.93)
    parser.add_argument("--max-restarts", type=integer_at_least(1), default=10)
    parser.add_argument("--max-iter", type=integer_at_least(1), default=800)
    parser.add_argument("--top-plateaus", type=integer_at_least(1), default=3)
    parser.add_argument("--bootstrap-replicates", type=integer_at_least(1), default=199)
    parser.add_argument("--bootstrap-alpha", type=float, default=0.05)
    parser.add_argument("--random-seed", type=integer_at_least(0), default=42)
    parser.add_argument("--bootstrap-seed", type=integer_at_least(0), default=20260913)
    return parser.parse_args()


def load_covariance(path: Path) -> pd.DataFrame:
    covariance = pd.read_pickle(path)
    if not isinstance(covariance, pd.DataFrame):
        raise ValueError("Input must be a pandas DataFrame with species labels.")
    if covariance.shape[0] < 2 or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("Covariance must be square with at least two species.")
    if not covariance.index.is_unique or not covariance.columns.is_unique:
        raise ValueError("Species labels must be unique.")
    if not covariance.index.equals(covariance.columns):
        raise ValueError("Row and column species labels must match in the same order.")
    if np.iscomplexobj(covariance.to_numpy()):
        raise ValueError("Covariance must be real.")
    matrix = covariance.to_numpy(dtype=float)
    if not np.isfinite(matrix).all() or not np.allclose(matrix, matrix.T, rtol=1e-10, atol=1e-12):
        raise ValueError("Covariance must be finite and symmetric.")
    if np.linalg.eigvalsh((matrix + matrix.T) / 2).min() <= 0:
        raise ValueError("Covariance must be positive definite.")
    return covariance


def main() -> int:
    args = parse_args()
    if args.fit_omega_ref != (args.omega_ref is None):
        raise SystemExit("Use --fit-omega-ref without --omega-ref, or --no-fit-omega-ref with a numeric --omega-ref.")
    covariance = load_covariance(args.input)
    args.output_root.mkdir(parents=True, exist_ok=True)
    output_dir = Path(tempfile.mkdtemp(prefix=f"{args.input.stem}_", dir=args.output_root))
    summary = {
        "status": "recovering",
        "input": str(args.input.resolve()),
        "settings": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
        "num_species": len(covariance),
        "species": [str(label) for label in covariance.columns],
        "package_versions": {name: version(name) for name in ("lambda-support-recovery", "numpy", "pandas", "scipy")},
    }

    def save_summary() -> None:
        (output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    def progress(message: str) -> None:
        print(message, flush=True)

    save_summary()
    progress(f"Output directory: {output_dir.resolve()}")
    progress(f"Covariance: {covariance.shape}; observations: {args.num_samples}; workers: {args.n_jobs}")
    try:
        result = select_support(
            covariance.to_numpy(dtype=float), num_samples=args.num_samples,
            support_scope=args.support_scope, nested_supports=True,
            omega_ref=args.omega_ref, fit_omega_ref=args.fit_omega_ref, kappa=args.kappa,
            max_restarts=args.max_restarts, max_iter=args.max_iter,
            random_seed=args.random_seed,
            method=args.method, top_plateaus=args.top_plateaus,
            bootstrap_replicates=args.bootstrap_replicates,
            bootstrap_alpha=args.bootstrap_alpha, bootstrap_seed=args.bootstrap_seed,
            n_jobs=args.n_jobs, return_result=True, progress=progress,
        )
        pd.to_pickle(result.curve, output_dir / "curve.pkl")
        pd.to_pickle(result, output_dir / "result.pkl")
        pd.DataFrame(result.support, index=covariance.index, columns=covariance.columns).to_pickle(output_dir / "support.pkl")
        pd.DataFrame(result.fitted_lambda, index=covariance.index, columns=covariance.columns).to_pickle(output_dir / "fitted_lambda.pkl")
        summary.update(
            status="complete",
            selected_dimension=int(result.selected_dimension),
            selected_edges=[[int(i), int(j)] for i, j in result.selected_edges],
            selected_species_edges=[[str(covariance.columns[i]), str(covariance.columns[j])] for i, j in result.selected_edges],
            fitted_omega=float(result.fitted_omega),
        )
        save_summary()
        progress(f"Selected dimension: {result.selected_dimension}; off-diagonal edges: {len(result.selected_edges)}")
        progress(f"Saved result, support, fitted Lambda, curve, and summary to {output_dir}")
    except Exception as exc:
        summary.update(status="failed", failed_stage=summary["status"], error=f"{type(exc).__name__}: {exc}")
        save_summary()
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
