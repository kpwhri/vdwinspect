from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]

_DATA_DIR = Path(__file__).resolve().parent / 'data'
_FORMAT_REGISTRY = None


def get_format(name: str):
    global _FORMAT_REGISTRY
    if _FORMAT_REGISTRY is None:
        _FORMAT_REGISTRY = TomlFormatRegistry()
    return _FORMAT_REGISTRY.get(name)


@dataclass(frozen=True)
class FormatSpec:
    name: str
    mapping: dict[str, str]
    default: str = 'bad'

    @property
    def valid_codes(self) -> set[str]:
        return set(self.mapping)


def _clean_str(x: Any) -> str:
    if x is None:
        return ''
    if not isinstance(x, str):
        x = str(x)
    return x.strip()


def _load_mapping_from_csv(
        csv_path: Path,
        *,
        code_col: str = 'code',
        label_col: str = 'label',
) -> dict[str, str]:
    if not csv_path.exists():
        raise FileNotFoundError(f'format CSV not found: {csv_path}')

    df = pl.read_csv(
        str(csv_path),
        null_values=['', '.', 'NA', 'null', 'None'],
        infer_schema_length=1000,
        truncate_ragged_lines=True,
    )

    if code_col not in df.columns or label_col not in df.columns:
        raise ValueError(
            f'format CSV {csv_path} must have columns {code_col!r} and {label_col!r}; '
            f'found: {df.columns}'
        )

    df = (
        df.select(
            pl.col(code_col).cast(pl.Utf8).str.strip_chars().alias('code'),
            pl.col(label_col).cast(pl.Utf8).str.strip_chars().alias('label'),
        )
        .filter(pl.col('code').is_not_null() & (pl.col('code') != ''))
    )

    dupes = df.group_by('code').len().filter(pl.col('len') > 1).select('code')
    if dupes.height:
        raise ValueError(f'duplicate codes in CSV {csv_path}: {dupes.to_series().to_list()}')

    return dict(zip(df['code'].to_list(), df['label'].to_list()))


class TomlFormatRegistry:
    """
    Top-level TOML format definition supports either:
      - inline mapping: mapping = { ... }
      - CSV mapping: csv_path = '...'
        optional: csv_code_col, csv_label_col

    Example TOML:

      [flg]
      default = 'bad'
      mapping = { Y = 'yes', N = 'no', U = 'unknown', E = 'external' }

      [lang_iso]
      default = 'bad'
      csv_path = 'reference/formats/lang_iso.csv'
    """

    def __init__(self, *, toml_path: str | Path | None = None, base_dir: str | Path | None = None):
        self.toml_path = Path(toml_path) if toml_path else _DATA_DIR / 'formats.toml'
        self.base_dir = Path(base_dir) if base_dir else _DATA_DIR
        self._raw: dict[str, Any] | None = None
        self._cache: dict[str, FormatSpec] = {}

    @property
    def raw(self):
        if not self._raw:
            self._load_raw()
        return self._raw

    def _load_raw(self):
        if self._raw is not None:
            return self._raw

        if tomllib is None:
            raise RuntimeError('tomllib is not available. Use Python 3.11+ or add a TOML parser dependency.')

        if not self.toml_path.exists():
            raise FileNotFoundError(f'formats TOML not found: {self.toml_path}')

        raw = tomllib.loads(self.toml_path.read_text(encoding='utf-8'))
        if not isinstance(raw, dict):
            raise ValueError('Formats TOML must parse to a dictionary')
        self._raw = raw

    def get(self, name: str) -> FormatSpec:
        name = _clean_str(name)

        if name in self._cache:
            return self._cache[name]

        raw = self.raw
        if name not in raw:
            raise KeyError(f'Format not defined in TOML: {name}')

        entry = raw[name]
        if not isinstance(entry, dict):
            raise ValueError(f'[{name}] must be a table')

        default = _clean_str(entry.get('default', 'bad'))
        if default == '':
            raise ValueError(f'[{name}].default must be a non-empty string')

        has_inline = 'mapping' in entry
        has_csv = 'csv_path' in entry
        if has_inline and has_csv:
            raise ValueError(f'[{name}] must use either inline mapping or csv_path, not both.')
        if not has_inline and not has_csv:
            raise ValueError(f'[{name}] must define mapping or csv_path.')

        if has_inline:
            mapping_raw = entry.get('mapping')
            if not isinstance(mapping_raw, dict) or not mapping_raw:
                raise ValueError(f'[{name}].mapping must be a non-empty table')

            mapping: dict[str, str] = {}
            for k, v in mapping_raw.items():
                code = _clean_str(k)
                label = _clean_str(v)
                if code == '':
                    raise ValueError(f'[{name}].mapping contains a blank code')
                if code in mapping:
                    raise ValueError(f'duplicate code in [{name}].mapping: {code}')
                mapping[code] = label

        else:
            csv_path = _clean_str(entry.get('csv_path'))
            if csv_path == '':
                raise ValueError(f'[{name}].csv_path must be a non-empty string')

            code_col = _clean_str(entry.get('csv_code_col', 'code')) or 'code'
            label_col = _clean_str(entry.get('csv_label_col', 'label')) or 'label'
            mapping = _load_mapping_from_csv(self.base_dir / csv_path, code_col=code_col, label_col=label_col)

        spec = FormatSpec(name=name, mapping=mapping, default=default)
        self._cache[name] = spec
        return spec

    def list_formats(self) -> list[str]:
        raw = self._load_raw()
        return sorted([k for k, v in raw.items() if isinstance(v, dict)])
