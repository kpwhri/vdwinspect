import polars as pl
import pytest
from vdwinspect.reference.expected_vars import load_expected_vars_csv


def test_load_expected_vars_default():
    df = load_expected_vars_csv()
    assert isinstance(df, pl.DataFrame)
    assert 'dset' in df.columns
    assert 'name' in df.columns
    # ensure 'lang' df is present
    lang_vars = df.filter(pl.col('dset') == 'lang')
    assert lang_vars.height >= 4
    expected_names = {'mrn', 'lang_iso', 'lang_usage', 'lang_primary'}
    assert expected_names.issubset(set(lang_vars['name'].to_list()))


def test_load_expected_vars_custom_path(tmp_path):
    csv_path = tmp_path / 'custom_vars.csv'
    csv_path.write_text('dset,name,type,length\ntest,var1,char,10\n')

    df = load_expected_vars_csv(str(csv_path))
    assert df.height == 1
    assert df[0, 'dset'] == 'test'
    assert df[0, 'name'] == 'var1'


def test_expected_vars_no_duplicates():
    df = load_expected_vars_csv()
    # check for (dset, name) duplicates
    dupes = (
        df.group_by(['dset', 'name'])
        .len()
        .filter(pl.col('len') > 1)
    )
    assert dupes.height == 0, f'Duplicate (dset, name) pairs found: {dupes}'


def test_expected_vars_names_non_empty():
    df = load_expected_vars_csv()
    assert df.filter(pl.col('name') == '').height == 0
    assert df.filter(pl.col('dset') == '').height == 0
