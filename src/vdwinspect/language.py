from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from loguru import logger
import polars as pl

from vdwinspect.common import QaRunSpec, build_checks_lf, standardize_bad_rows, put_expr
from vdwinspect.reference.expected_vars import load_expected_vars_csv
from vdwinspect.reference.registry import FormatSpec, get_format


def compute_lang_stats_lf(
        lang_lf: pl.LazyFrame,
        *,
        siteabbr: str,
) -> pl.LazyFrame:
    mult_lang_lf = (
        lang_lf.select(['mrn', 'lang_iso'])
        .unique(subset=['mrn', 'lang_iso'], keep='first')
        .group_by('mrn')
        .agg(pl.len().alias('lang_cnt'))
        .filter(pl.col('lang_cnt') > 1)
    )

    mrns_mult_use_b_lf = (
        lang_lf.filter(pl.col('lang_usage') == 'B')
        .select(['mrn', 'lang_iso'])
        .unique(subset=['mrn', 'lang_iso'], keep='first')
        .group_by('mrn')
        .agg(pl.len().alias('cnt_langs_with_b'))
        .filter(pl.col('cnt_langs_with_b') > 1)
        .select('mrn')
    )

    base_stats_lf = lang_lf.select(
        pl.len().alias('lang_recs'),
        pl.n_unique('mrn').alias('lang_subj'),
        (pl.when(pl.col('lang_iso') == 'eng').then(pl.col('mrn')).otherwise(None)).n_unique().alias('lang_eng'),
        (pl.when(pl.col('lang_iso') != 'eng').then(pl.col('mrn')).otherwise(None)).n_unique().alias('lang_ne'),
        pl.n_unique('lang_iso').alias('lang_count'),
    )

    mult_stats_lf = mult_lang_lf.select(
        pl.len().alias('lang_mult'),
        pl.max('lang_cnt').fill_null(0).alias('max_lang'),
    )

    use_mult_lf = mrns_mult_use_b_lf.select(pl.len().alias('use_mult'))

    return (
        base_stats_lf
        .join(mult_stats_lf, how='cross')
        .join(use_mult_lf, how='cross')
        .with_columns(pl.lit(siteabbr).alias('siteabbr'))
    )


def lang_tier_one(
        lang_df: pl.DataFrame,
        *,
        outdir: Path,
        siteabbr: str,
        warn_lim: float = 2.0,
        fail_lim: float = 5.0,
        normalize: bool = True,
        out_format: Literal['parquet', 'csv', 'ipc'] = 'csv',
) -> dict[str, pl.DataFrame]:
    spec = QaRunSpec(
        dset='lang',
        function='lang_tier_one',
        detail_dset='bad_lang',
        out_share=outdir / 'share',
        out_local=outdir / 'local',
        out_format=out_format,
        key_cols=('mrn', 'lang_iso', 'lang_usage'),
        warn_lim=warn_lim,
        fail_lim=fail_lim,
    )
    logger.info(f'Running tier1 languages check: {spec}.')

    expected_lf = load_expected_vars_csv().lazy()
    lang_lf = lang_df.lazy()

    if normalize:
        lang_lf = lang_lf.with_columns(
            pl.col('lang_iso').cast(pl.Utf8).str.strip_chars(),
            pl.col('lang_usage').cast(pl.Utf8).str.strip_chars(),
            pl.col('lang_primary').cast(pl.Utf8).str.strip_chars(),
        )

    lang_lf = lang_lf.sort(list(spec.key_cols))

    lang_checks_lf = build_checks_lf(expected_lf, spec=spec)

    bad_iso_lf = standardize_bad_rows(
        lang_lf.filter(put_expr('lang_iso', get_format('lang')) == 'bad'),
        spec=spec,
        problem='bad value in lang_iso',
        check_column='lang_iso',
        value_expr=pl.col('lang_iso'),
    )

    bad_usage_lf = standardize_bad_rows(
        lang_lf.filter(put_expr('lang_usage', get_format('use')) == 'bad'),
        spec=spec,
        problem='bad value in lang_usage',
        check_column='lang_usage',
        value_expr=pl.col('lang_usage'),
    )

    bad_primary_lf = standardize_bad_rows(
        lang_lf.filter(put_expr('lang_primary', get_format('flg')) == 'bad'),
        spec=spec,
        problem='bad value in lang_primary',
        check_column='lang_primary',
        value_expr=pl.col('lang_primary'),
    )

    dup_keys_lf = (
        lang_lf.group_by(list(spec.key_cols))
        .len()
        .filter(pl.col('len') > 1)
        .select(list(spec.key_cols))
    )

    dup_rows_lf = standardize_bad_rows(
        lang_lf.join(dup_keys_lf, on=list(spec.key_cols), how='inner'),
        spec=spec,
        problem='dupe rec in lang_iso',
        check_column='mrn/lang_iso/lang_usage',
        value_expr=pl.lit(None, dtype=pl.Utf8),
    )

    bad_lang_lf = pl.concat([bad_iso_lf, bad_usage_lf, bad_primary_lf, dup_rows_lf], how='diagonal_relaxed')

    # keep first of any duplicates - not used?
    # lang_recs_nd_lf = lang_lf.unique(subset=list(spec.key_cols), keep='first')

    lang_stats_lf = compute_lang_stats_lf(lang_lf, siteabbr=siteabbr)

    bad_lang_summary_lf = (
        bad_lang_lf
        .group_by('problem')
        .agg(pl.len().alias('num_bad'))
        .join(lang_stats_lf.select(pl.col('lang_recs').alias('num_lang_recs')), how='cross')
        .with_columns((pl.col('num_bad') / pl.col('num_lang_recs') * 100).alias('percent_bad'))
        .select(['problem', 'num_bad', 'percent_bad'])
    )

    unexpected_problems_lf = (
        bad_lang_summary_lf
        .join(lang_checks_lf.select('problem'), on='problem', how='anti')
        .select('problem')
    )

    lang_rbr_checks_lf = (
        lang_checks_lf
        .join(bad_lang_summary_lf, on='problem', how='left')
        .with_columns(
            pl.col('num_bad').fill_null(0),
            pl.col('percent_bad').fill_null(0.0),
        )
        .with_columns(
            pl.when(pl.col('percent_bad') > pl.col('fail_lim')).then(pl.lit('fail'))
            .when(pl.col('percent_bad') > pl.col('warn_lim')).then(pl.lit('warning'))
            .otherwise(pl.lit('pass'))
            .alias('result')
        )
    )

    results_lf = (
        lang_rbr_checks_lf
        .select(
            'description',
            pl.lit(spec.function).alias('qa_macro'),
            pl.lit('local/bad_lang').alias('detail_dset'),
            'num_bad',
            'percent_bad',
            'result',
        )
    )

    logger.info(f'Writing lang_stats to share: {spec.out_share}')
    spec.write_share(lang_stats_lf.collect(), 'lang_stats')
    logger.info(f'Writing bad_lang to local (debug-only): {spec.out_local}')
    spec.write_local(bad_lang_lf.collect(), 'bad_lang')
    spec.write_local(bad_lang_summary_lf.collect(), 'bad_lang_summary')

    return {
        'unexpected_problems': unexpected_problems_lf.collect(),
        'results': results_lf.collect(),
    }


def run_lang_qa(lang_df: pl.DataFrame, siteabbr: str = 'SITE', outdir: Path = None,
                **kwargs) -> dict[str, pl.DataFrame]:
    if outdir is None:
        outdir = Path('.')
        logger.warning(f'Default to outputting results to current directory: {outdir}.')

    return lang_tier_one(
        lang_df,
        siteabbr=siteabbr,
        outdir=outdir,
        **kwargs,
    )
