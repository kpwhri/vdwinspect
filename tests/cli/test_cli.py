import polars as pl
import pytest
from typer.testing import CliRunner
from vdwinspect.cli import app
from pathlib import Path
import vdwcore
from unittest import mock

runner = CliRunner()


@pytest.fixture
def mock_sv():
    with mock.patch('vdwinspect.cli.make_stdvars_from_config') as mock_make:
        sv = mock.Mock()
        # simulate a simple vdw_languages
        sv.vdw_languages = pl.DataFrame({
            'mrn': ['Vainamoinen'],
            'lang_iso': ['fin'],
            'lang_usage': ['B'],
            'lang_primary': ['Y']
        })
        mock_make.return_value = sv
        yield sv


def test_cli_help():
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'vdwinspect CLI for running QAs.' in result.stdout


def test_cli_languages_no_config():
    # missing config_paths argument
    result = runner.invoke(app, ['--qa', 'languages'])
    assert result.exit_code != 0
    assert 'Missing argument' in result.stderr or 'Missing argument' in result.stdout


def test_cli_languages_with_config(mock_sv, tmp_path):
    config_file = tmp_path / 'site.toml'
    config_file.write_text('[table_map]\nlanguage="lang"')

    outdir = tmp_path / 'output'

    with mock.patch('vdwinspect.language.run_lang_qa') as mock_run:
        result = runner.invoke(app, [
            str(config_file), '--qa', 'languages', '--siteabbr', 'SITE', '--outdir', str(outdir)
        ])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] is mock_sv.vdw_languages
        assert kwargs['siteabbr'] == 'SITE'
        assert kwargs['outdir'] == outdir


def test_cli_languages_explicit_kwargs(mock_sv, tmp_path):
    config_file = tmp_path / 'site.toml'
    config_file.write_text('[table_map]\nlanguage="lang"')

    with mock.patch('vdwinspect.language.run_lang_qa') as mock_run:
        result = runner.invoke(app, [
            str(config_file), '--qa', 'languages',
            '--warn-lim', '10.0',
            '--fail-lim', '20.0',
            '--no-normalize',
            '--out-format', 'parquet'
        ])

        assert result.exit_code == 0
        _, kwargs = mock_run.call_args
        assert kwargs['warn_lim'] == 10.0
        assert kwargs['fail_lim'] == 20.0
        assert kwargs['normalize'] is False
        assert kwargs['out_format'] == 'parquet'


def test_cli_languages_all(mock_sv, tmp_path):
    config_file = tmp_path / 'site.toml'
    config_file.write_text('[table_map]\nlanguage="lang"')

    with mock.patch('vdwinspect.language.run_lang_qa') as mock_run:
        result = runner.invoke(app, [str(config_file), '--qa', 'all'])

        assert result.exit_code == 0
        mock_run.assert_called_once()


def test_cli_multiple_configs(mock_sv, tmp_path):
    config1 = tmp_path / 'config1.toml'
    config1.write_text('[table_map]\nlanguage="lang"')
    config2 = tmp_path / 'config2.toml'
    config2.write_text('engine="sqlite:///"')

    with mock.patch('vdwinspect.language.run_lang_qa'):
        result = runner.invoke(app, [str(config1), str(config2), '--qa', 'languages'])
        assert result.exit_code == 0


def test_cli_html_report_generation(mock_sv, tmp_path):
    config_file = tmp_path / 'site.toml'
    config_file.write_text('[table_map]\nlanguage="lang"')

    results_df = pl.DataFrame({
        'description': ['Test'],
        'qa_macro': ['run_lang_qa'],
        'detail_dset': ['local/bad'],
        'num_bad': [0],
        'percent_bad': [0.0],
        'result': ['pass']
    })

    with mock.patch('vdwinspect.language.run_lang_qa', return_value={'results': results_df}):
        result = runner.invoke(app, [
            str(config_file),
            '--qa', 'languages',
            '--siteabbr', 'UKKO',
            '--outdir', str(tmp_path)
        ])

        assert result.exit_code == 0
        report_path = tmp_path / 'UKKO_qa_report.html'
        assert report_path.exists()
        content = report_path.read_text()
        assert 'vdwinspect QA Report - UKKO' in content
        assert 'QA: languages' in content
        assert 'Site: UKKO' in content
        assert 'Tier 1 Checks' in content
        assert 'Test' in content
