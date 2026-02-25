import polars as pl
import pytest
from pathlib import Path

from vdwinspect.common import QaRunSpec


@pytest.mark.parametrize('out_format,reader', [
    ('parquet', pl.read_parquet),
    ('csv', pl.read_csv),
    ('ipc', pl.read_ipc),
])
def test_qarunspec_writes_and_creates_dirs(tmp_path: Path, out_format, reader):
    # given non-existent directories
    out_share = tmp_path / 'share' / 'reports'
    out_local = tmp_path / 'local' / 'reports'

    assert not out_share.exists()
    assert not out_local.exists()

    spec = QaRunSpec(
        dset='sampo',
        function='ilmarinen_check',
        key_cols=('ainikki',),
        out_share=out_share,
        out_local=out_local,
        out_format=out_format,
    )

    assert out_share.exists() and out_share.is_dir()
    assert out_local.exists() and out_local.is_dir()

    df = pl.DataFrame({'sankari': ['Väinämöinen', 'Ilmarinen'], 'arvo': [1, 2]})

    local_path = spec.write_local(df, name='koe')
    share_path = spec.write_share(df, name='raportti')

    assert local_path.exists()
    assert share_path.exists()

    # verify contents round-trip
    read_local_df = reader(str(local_path))
    read_share_df = reader(str(share_path))

    assert read_local_df.shape == df.shape
    assert read_share_df.shape == df.shape
    # check that a known column round-trips
    assert read_local_df.select(pl.col('arvo').sum()).item() == 3
    assert read_share_df.select(pl.col('arvo').sum()).item() == 3
