from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import polars as pl

from vdwinspect.reference.registry import FormatSpec


@dataclass(frozen=True)
class QaRunSpec:
    dset: str
    function: str
    key_cols: tuple[str, ...]
    out_share: Path
    out_local: Path
    out_format: Literal['parquet', 'csv', 'ipc'] = 'csv'
    siteabbr: str = 'SITE'
    detail_dset: str | None = None
    exclude_from_checks: tuple[str, ...] = ('mrn',)
    warn_lim: float = 2.0
    fail_lim: float = 5.0

    def __post_init__(self) -> None:
        # ensure output directories exist
        for p in (self.out_share, self.out_local):
            p.mkdir(parents=True, exist_ok=True)

    def _write(self, df: pl.DataFrame, base_dir: Path, name: str) -> Path:
        # build path with correct extension and write using polars
        ext = self.out_format
        path = base_dir / f'{name}.{ext}'
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.out_format == 'parquet':
            df.write_parquet(str(path))
        elif self.out_format == 'csv':
            df.write_csv(str(path))
        elif self.out_format == 'ipc':
            df.write_ipc(str(path))
        else:
            raise ValueError(f'unsupported out_format: {self.out_format}')
        return path

    def write_local(self, df: pl.DataFrame, name: str) -> Path:
        """Write dataframe to the local output directory using the configured format."""
        return self._write(df, self.out_local, name)

    def write_share(self, df: pl.DataFrame, name: str) -> Path:
        """Write dataframe to the shared output directory using the configured format."""
        return self._write(df, self.out_share, f'{self.siteabbr}_{name}')


def append_results(results_df: pl.DataFrame | None, results_rows: pl.DataFrame) -> pl.DataFrame:
    if results_df is None or results_df.is_empty():
        return results_rows
    return pl.concat([results_df, results_rows], how='diagonal_relaxed')


def put_expr(col: str, fmt: FormatSpec) -> pl.Expr:
    return pl.col(col).replace(fmt.mapping, default=fmt.default)


def build_checks_lf(
        expected_vars_lf: pl.LazyFrame,
        *,
        spec: QaRunSpec,
) -> pl.LazyFrame:
    return (
        expected_vars_lf
        .filter((pl.col('dset') == spec.dset) & (~pl.col('name').is_in(list(spec.exclude_from_checks))))
        .select(
            pl.concat_str([pl.lit('Valid values: '), pl.col('name').cast(pl.Utf8).str.strip_chars()]).alias(
                'description'),
            pl.concat_str([pl.lit('bad value in '), pl.col('name').cast(pl.Utf8).str.strip_chars()]).alias('problem'),
            pl.lit(spec.warn_lim).alias('warn_lim'),
            pl.lit(spec.fail_lim).alias('fail_lim'),
        )
    )


def standardize_bad_rows(
        base_lf: pl.LazyFrame,
        *,
        spec: QaRunSpec,
        problem: str,
        check_column: str,
        value_expr: pl.Expr,
) -> pl.LazyFrame:
    key_cols = list(spec.key_cols)
    kept_cols = [c for c in key_cols if c in base_lf.collect_schema().names()]
    return (
        base_lf
        .select(
            [
                pl.lit(spec.dset).alias('qa_dset'),
                pl.lit(spec.function).alias('qa_macro'),
                pl.lit(problem).alias('problem'),
                pl.lit(check_column).alias('check_column'),
                value_expr.alias('value'),
                *[pl.col(c) for c in kept_cols],
            ]
        )
    )
