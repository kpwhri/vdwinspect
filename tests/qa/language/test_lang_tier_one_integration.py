import polars as pl
import pytest
from vdwinspect.language import lang_tier_one


def test_lang_tier_one_valid(lang_df_valid, tmp_path):
    """Test with all valid values."""
    siteabbr = 'SITE'
    results = lang_tier_one(lang_df_valid, siteabbr=siteabbr, outdir=tmp_path)

    assert pl.read_csv(tmp_path / 'local' / f'bad_lang.csv').height == 0
    assert results['unexpected_problems'].height == 0

    stats = pl.read_csv(tmp_path / 'share' / f'{siteabbr}_lang_stats.csv')
    assert stats[0, 'lang_recs'] == 4
    assert stats[0, 'lang_subj'] == 3
    assert stats[0, 'lang_mult'] == 1  # has 2 languages
    assert stats[0, 'max_lang'] == 2

    # all checks pass
    rbr = results['results']
    assert (rbr['result'] == 'pass').all()


def test_lang_tier_one_invalid(lang_df_invalid, tmp_path):
    """Test with invalid codes and duplicates."""
    siteabbr = 'SITE'
    results = lang_tier_one(lang_df_invalid, siteabbr=siteabbr, outdir=tmp_path)

    bad_lang = pl.read_csv(tmp_path / 'local' / f'bad_lang.csv')
    assert bad_lang.height == 5  # 3 bad values + 2 duplicate rows

    problems = bad_lang['problem'].to_list()
    assert 'bad value in lang_iso' in problems
    assert 'bad value in lang_usage' in problems
    assert 'bad value in lang_primary' in problems
    assert 'dupe rec in lang_iso' in problems

    # duplicate detection
    dupes = bad_lang.filter(pl.col('problem') == 'dupe rec in lang_iso')
    assert dupes.height == 2
    assert (dupes['mrn'] == 'Ukko').all()

    # bad_lang_summary correct counts
    summary = pl.read_csv(tmp_path / 'local' / 'bad_lang_summary.csv')
    assert summary.filter(pl.col('problem') == 'bad value in lang_iso')[0, 'num_bad'] == 1
    assert summary.filter(pl.col('problem') == 'dupe rec in lang_iso')[0, 'num_bad'] == 2


def test_lang_tier_one_results_schema(lang_df_valid, tmp_path):
    """Assert results_rows schema."""
    results = lang_tier_one(lang_df_valid, siteabbr='SITE', outdir=tmp_path)
    df = results['results']

    expected_cols = {'description', 'qa_macro', 'detail_dset', 'num_bad', 'percent_bad', 'result'}
    assert set(df.columns) == expected_cols

    assert (df['percent_bad'] >= 0).all()
    assert (df['percent_bad'] <= 100).all()
    assert df['result'].is_in(['pass', 'warning', 'fail']).all()


def test_lang_tier_one_stats_correctness(tmp_path):
    """More detailed stats verification."""
    siteabbr = 'SITE'
    df = pl.DataFrame({
        'mrn': ['A', 'A', 'B', 'B', 'C'],
        'lang_iso': ['fin', 'swe', 'fin', 'swe', 'fin'],
        'lang_usage': ['B', 'B', 'S', 'W', 'B'],
        'lang_primary': ['Y', 'N', 'Y', 'N', 'Y']
    })
    results = lang_tier_one(df, siteabbr=siteabbr, outdir=tmp_path)

    stats = pl.read_csv(tmp_path / 'share' / f'{siteabbr}_lang_stats.csv')
    assert stats[0, 'lang_recs'] == 5
    assert stats[0, 'lang_subj'] == 3
    assert stats[0, 'lang_mult'] == 2  # A and B have 2 languages
    assert stats[0, 'use_mult'] == 1
