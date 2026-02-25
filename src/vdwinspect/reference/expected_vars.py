from pathlib import Path

import polars as pl

_DATA_DIR = Path(__file__).resolve().parent / 'data'


def load_expected_vars_csv(path: str = None) -> pl.DataFrame:
    if path is None:
        path = _DATA_DIR / 'expected_vars.csv'
    return (
        pl.read_csv(
            path,
            null_values=['', '.', 'NA', 'null', 'None'],
            infer_schema_length=1000,
        )
        .with_columns(
            pl.col('dset').cast(pl.Utf8).str.strip_chars(),
            pl.col('name').cast(pl.Utf8).str.strip_chars(),
            pl.col('type').cast(pl.Int64, strict=False),
            pl.col('length').cast(pl.Int64, strict=False),
        )
    )
