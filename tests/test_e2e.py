import polars as pl
import pytest

from vdwinspect.language import lang_tier_one


def test_e2e_lang(lang_df_valid, tmp_path):
    """End-to-end smoke test for the library."""
    siteabbr = 'SITE'
    results = lang_tier_one(lang_df_valid, siteabbr=siteabbr, outdir=tmp_path)

    res_df = results['results']
    required_cols = {'description', 'qa_macro', 'detail_dset', 'num_bad', 'percent_bad', 'result'}
    assert required_cols.issubset(set(res_df.columns))

    assert res_df['result'].is_in(['pass', 'warning', 'fail']).all()
    assert res_df['percent_bad'].dtype in (pl.Float32, pl.Float64)
    assert (res_df['percent_bad'] >= 0).all()
    assert (res_df['percent_bad'] <= 100).all()

    # verify other required tables are present
    assert (tmp_path / 'local' / 'bad_lang.csv').exists()
    assert (tmp_path / 'local' / 'bad_lang_summary.csv').exists()
    assert (tmp_path / 'share' / f'{siteabbr}_lang_stats.csv').exists()
