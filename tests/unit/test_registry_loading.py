import pytest
import tomllib
from pathlib import Path
from vdwinspect.reference.registry import TomlFormatRegistry, FormatSpec


def test_registry_loading_success(temp_registry_setup):
    reg = temp_registry_setup

    # test inline mapping
    use_fmt = reg.get('use')
    assert isinstance(use_fmt, FormatSpec)
    assert use_fmt.name == 'use'
    assert use_fmt.default == 'bad'
    assert use_fmt.mapping == {'B': 'Both', 'S': 'Spoken', 'W': 'Written'}
    assert use_fmt.valid_codes == {'B', 'S', 'W'}

    # test csv mapping
    lang_fmt = reg.get('lang')
    assert lang_fmt.name == 'lang'
    assert 'fin' in lang_fmt.valid_codes
    assert lang_fmt.mapping['fin'] == 'Finnish'


def test_registry_missing_toml(tmp_path):
    reg = TomlFormatRegistry(toml_path=tmp_path / 'missing.toml')
    with pytest.raises(FileNotFoundError):
        reg.get('any')


def test_registry_invalid_toml(tmp_path):
    toml_file = tmp_path / 'invalid.toml'
    toml_file.write_text('this is not toml')
    reg = TomlFormatRegistry(toml_path=toml_file)
    with pytest.raises(Exception):  # tomllib raises specific errors
        reg.get('any')


def test_registry_both_mapping_and_csv(tmp_path):
    data_dir = tmp_path
    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
mapping = { A = 'B' }
csv_path = 'something.csv'
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='must use either inline mapping or csv_path, not both'):
        reg.get('fail')


def test_registry_neither_mapping_nor_csv(tmp_path):
    data_dir = tmp_path
    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
default = 'bad'
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='must define mapping or csv_path'):
        reg.get('fail')


def test_registry_csv_missing_columns(tmp_path):
    data_dir = tmp_path
    csv_file = data_dir / 'bad.csv'
    csv_file.write_text('wrong,cols\n1,2')

    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
csv_path = 'bad.csv'
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='must have columns'):
        reg.get('fail')


def test_registry_duplicate_codes_csv(tmp_path):
    data_dir = tmp_path
    csv_file = data_dir / 'dupes.csv'
    csv_file.write_text('code,label\nA,Alpha\nA,Duplicate')

    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
csv_path = 'dupes.csv'
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='duplicate codes in CSV'):
        reg.get('fail')


def test_registry_duplicate_codes_inline(tmp_path):
    # tomllib actually catches duplicate keys in same table
    data_dir = tmp_path
    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
mapping = { " A " = "Alpha", "A" = "Duplicate" }
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='duplicate code in'):
        reg.get('fail')


def test_registry_empty_default(tmp_path):
    data_dir = tmp_path
    toml_file = data_dir / 'fail.toml'
    toml_content = """
[fail]
default = ""
mapping = { A = 'B' }
"""
    toml_file.write_text(toml_content)
    reg = TomlFormatRegistry(toml_path=toml_file, base_dir=data_dir)
    with pytest.raises(ValueError, match='default must be a non-empty string'):
        reg.get('fail')
