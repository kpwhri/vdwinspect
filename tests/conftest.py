import polars as pl
import pytest
from vdwinspect.reference.registry import TomlFormatRegistry


@pytest.fixture
def lang_df_valid():
    """Returns a valid small language dataset with Kalevala names."""
    return pl.DataFrame({
        'mrn': ['Vainamoinen', 'Ilmarinen', 'Lemminkainen', 'Vainamoinen'],
        'lang_iso': ['fin', 'fin', 'swe', 'swe'],
        'lang_usage': ['B', 'B', 'B', 'S'],
        'lang_primary': ['Y', 'Y', 'Y', 'N']
    })


@pytest.fixture
def lang_df_invalid():
    """Returns an invalid language dataset with bad codes and duplicates."""
    return pl.DataFrame({
        'mrn': [
            'Aino',  # Valid
            'Louhi',  # Invalid lang_iso
            'Joukahainen',  # Invalid lang_usage
            'Kullervo',  # Invalid lang_primary
            'Ukko',  # Duplicate key 1
            'Ukko',  # Duplicate key 2
        ],
        'lang_iso': ['fin', 'ZZZ', 'fin', 'fin', 'fin', 'fin'],
        'lang_usage': ['B', 'B', 'X', 'B', 'B', 'B'],
        'lang_primary': ['Y', 'Y', 'Y', 'Q', 'Y', 'Y']
    })


@pytest.fixture
def temp_registry_setup(tmp_path):
    """Fixture to create temporary TOML and CSV files for registry testing."""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()

    toml_path = data_dir / 'formats.toml'
    csv_path = data_dir / 'iso.csv'

    # create a sample CSV
    csv_content = 'code,label\nfin,Finnish\nswe,Swedish\neng,English\n'
    csv_path.write_text(csv_content)

    # create a sample TOML
    toml_content = f"""
[lang]
default = 'bad'
csv_path = 'iso.csv'

[use]
default = 'bad'
mapping = {{ B = 'Both', S = 'Spoken', W = 'Written' }}

[flg]
default = 'bad'
mapping = {{ Y = 'Yes', N = 'No' }}
"""
    toml_path.write_text(toml_content)

    return TomlFormatRegistry(toml_path=toml_path, base_dir=data_dir)
