from pathlib import Path
from typing import Any

import polars as pl
from great_tables import GT, style, loc


class QaReport:
    """Object for progressively building an HTML report."""

    def __init__(self, title: str = 'vdwinspect QA Report'):
        self.title = title
        self.elements: list[Any] = []

    def add_table(self, df: pl.DataFrame, title: str | None = None, subtitle: str | None = None) -> None:
        """Add a Polars DataFrame as a styled GT table to the report."""
        gt_tbl = GT(df, rowname_col=df.columns[0])

        if title or subtitle:
            gt_tbl = gt_tbl.tab_header(title=title, subtitle=subtitle)

        # style result column if it exists
        if 'result' in df.columns:
            gt_tbl = (
                gt_tbl
                .tab_style(
                    style=style.fill(color='green'),
                    locations=loc.body(
                        columns='result',
                        rows=pl.col('result') == 'pass'
                    )
                )
                .tab_style(
                    style=style.fill(color='red'),
                    locations=loc.body(
                        columns='result',
                        rows=pl.col('result') == 'fail'
                    )
                )
                .tab_style(
                    style=style.fill(color='yellow'),
                    locations=loc.body(
                        columns='result',
                        rows=~pl.col('result').is_in(['pass', 'fail'])
                    )
                )
            )

        self.elements.append(gt_tbl)

    def save(self, outpath: Path) -> None:
        """Write the report to an HTML file."""
        html_content = [
            '<html>',
            '<head>',
            f'<title>{self.title}</title>',
            '<style>',
            'body { font-family: sans-serif; margin: 2em; }',
            '.qa-element { margin-bottom: 4em; }',
            '</style>',
            '</head>',
            '<body>',
            f'<h1>{self.title}</h1>',
        ]

        for element in self.elements:
            html_content.append('<div class="qa-element">')
            if isinstance(element, GT):
                html_content.append(element.as_raw_html())
            else:
                # placeholder for figures or other types
                html_content.append(str(element))
            html_content.append('</div>')

        html_content.extend(['</body>', '</html>'])

        outpath.parent.mkdir(parents=True, exist_ok=True)
        outpath.write_text('\n'.join(html_content))
