from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
import polars as pl
from vdwcore import make_stdvars_from_config
from loguru import logger

from vdwinspect import language
from vdwinspect.report import QaReport

app = typer.Typer(add_completion=False)

# map of qa name to (sv_attribute, run_function_name)
QA_REGISTRY = {
    'languages': ('vdw_language', 'run_lang_qa'),
}


@app.command()
def main(
        config_paths: Annotated[list[Path], typer.Argument(help='Path(s) to toml config files')],
        site: Annotated[str, typer.Option(help='Site abbreviation')] = 'SITE',
        outdir: Annotated[Path, typer.Option(help='Output directory')] = Path('.'),
        qa: Annotated[list[str], typer.Option('--qa', help='QA(s) to run (e.g. languages). Use "all" for all.')] = None,
        warn_lim: Annotated[float, typer.Option(help='Warning limit percentage')] = 2.0,
        fail_lim: Annotated[float, typer.Option(help='Failure limit percentage')] = 5.0,
        normalize: Annotated[bool, typer.Option(help='Whether to normalize the data')] = True,
        out_format: Annotated[str, typer.Option(help='Output format (csv, parquet, ipc)')] = 'csv',
):
    """vdwinspect CLI for running QAs."""
    sv = make_stdvars_from_config(config_paths)

    qas_to_run = qa or []
    if 'all' in [q.lower() for q in qas_to_run]:
        qas_to_run = list(QA_REGISTRY.keys())

    if not qas_to_run:
        logger.warning('No QAs specified to run. Use --qa [name] or --qa all')
        return

    kwargs = {
        'warn_lim': warn_lim,
        'fail_lim': fail_lim,
        'normalize': normalize,
        'out_format': out_format,
    }

    report = QaReport(title=f'vdwinspect QA Report - {site}')
    has_results = False

    for qa_name in qas_to_run:
        if qa_name not in QA_REGISTRY:
            logger.error(f'Unknown QA: {qa_name}. Available: {list(QA_REGISTRY.keys())}')
            continue

        attr_name, run_func_name = QA_REGISTRY[qa_name]
        run_func = getattr(language, run_func_name)

        if not hasattr(sv, attr_name):
            logger.error(
                f'StdVars does not have {attr_name}. Check your config [table_map] and ensure the mapping is available.')
            continue

        logger.info(f'Running {qa_name} QA for {site}...')
        df = getattr(sv, attr_name).collect()
        results = run_func(df, siteabbr=site, outdir=outdir, **kwargs)

        if 'results' in results and isinstance(results['results'], pl.DataFrame):
            results_df = results['results']
            title = f'QA: {qa_name} - Site: {site}'
            subtitle = 'Tier 1 Checks'
            report.add_table(results_df, title=title, subtitle=subtitle)
            has_results = True

    if has_results:
        report_path = outdir / f'{site}_qa_report.html'
        logger.info(f'Generating HTML report: {report_path}')
        report.save(report_path)


if __name__ == '__main__':
    app()
