"""Save the rodent–flea data and species counts per region as CSV files."""

from pathlib import Path

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "Dataset" / "rodent_flea"


def aggregate_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per region, with host counts followed by flea counts."""
    regions = df["Region"].drop_duplicates()
    host_species = df["Host species"].drop_duplicates()
    flea_species = df.columns[3:]

    host_counts = (
        df.groupby(["Region", "Host species"], sort=False)["no hosts sampled"]
        .sum()
        .unstack(fill_value=0)
        .reindex(index=regions, columns=host_species, fill_value=0)
    )
    flea_counts = df.groupby("Region", sort=False)[flea_species].sum()

    result = pd.concat([host_counts, flea_counts], axis=1).reset_index()
    result.columns.name = None
    return result

def main() -> None:
    df = pd.read_csv(DATA_DIR / "DoublePhyloData.csv")
    regional_df = aggregate_by_region(df)

    df.to_csv(DATA_DIR / "DoublePhyloData_original.csv", index=False)
    regional_df.to_csv(DATA_DIR / "DoublePhyloData_by_region.csv", index=False)
    print(f"Saved original DataFrame: {df.shape}")
    print(f"Saved regional DataFrame: {regional_df.shape}")
    print(regional_df.head(10))


if __name__ == "__main__":
    main()
