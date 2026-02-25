# vdwinspect

VDW QA library and CLI for running standardized data quality checks and generating a shareable report.


## Requirements

- Python >= 3.10
- `uv` recommended for installs and development


## Installation

Install from a checked-out repo:
```bash
uv pip install .
```
Local development:
```bash
uv sync
uv run pytest
```

## Quickstart

1) Create a config file (example below).  
2) Run a QA and write outputs + report.

To run a single QA package:
```bash
vdwinspect config.toml --qa languages --site SITE --outdir ./output
```
Run all available QAs:
```bash
vdwinspect config.toml --qa all --site SITE --outdir ./output
```

Tune thresholds and output format:
```bash
vdwinspect config.toml --qa languages --warn-lim 1.0 --fail-lim 3.0 --out-format parquet
```

Outputs are written under `--outdir` and typically include:
- machine-readable outputs under `./output/share` and `./output/local`
- a consolidated HTML report at `./output/SITE_qa_report.html`


## Configuration (`config.toml`)

`vdwinspect` reads one or more toml config files. Later files can supplement or override earlier ones.

### Required keys

#### `engine` (connection string)

`engine` is the database connection string.

You may optionally use `{username}` and `{password}` placeholders in the connection string and provide the values in a separate toml file (see below).

#### `[table_map]` (VDW common name → actual table)

`[table_map]` maps **common VDW table names** (the names vdwinspect expects) to the **actual tables/views** in your
database.

Example (minimal):
```toml
engine = 'YOUR_CONNECTION_STRING_HERE'

[table_map]
vdw_language = 'lang'
```

### Optional keys

#### `schema`

If provided, this may be used by vdwinspect to qualify table references (depending on your database/dialect).
```toml
schema = 'DB_SCHEMA'
```

#### `username` / `password`

If your `engine` string contains `{username}` and `{password}`, you can provide:
```toml
username = 'YOUR_USERNAME_HERE'
password = 'YOUR_PASSWORD_HERE'
```
Place in a secure location if using username/password.

Example (placeholder substitution -- note these can be in different toml files in different parts of the file system):
```toml
engine = 'YOUR_DIALECT://{username}:{password}@YOUR_HOST:YOUR_PORT/YOUR_DB'

username = 'YOUR_USERNAME_HERE'
password = 'YOUR_PASSWORD_HERE'

[table_map]
vdw_language = 'lang'
```


### Using multiple config files

You can provide multiple config paths; they are merged:
```bash
vdwinspect site.toml db.toml secrets.toml --qa languages --site SITE --outdir ./output
```
A common pattern is:
- `site.toml` contains `table_map`, non-sensitive settings
- `db.toml` contains `engine` and `schema`
- `secrets.toml` contains `username`/`password` (if required)


## CLI reference

```bash
vdwinspect --help
```

Key options:
- `--qa`: which QA to run (`languages` or `all`)
- `--site`: site abbreviation used in report/output naming
- `--outdir`: output directory root
- `--out-format`: output dataset format (e.g., `parquet`, `csv`, `ipc`)
- `--warn-lim` / `--fail-lim`: thresholds used by checks


## Contributing / Pull Requests

Pull requests are welcome to add new QA processes.

Project layout (high-level):

- `src/vdwinspect/` — library + CLI implementation
- `tests/` — unit + integration tests
- `examples/` — example configuration(s)

Guidelines for changes:
1. Keep the change focused.
2. Add/extend tests for the expected behavior.
3. Ensure the new function is reachable from cli.
4. Update docs (README and/or example configs).
5. Update `CHANGELOG.md` under **Unreleased** with a short note.

### Suggested checklist for PRs

- [ ] Added/updated unit tests for the new behavior
- [ ] `uv run pytest` passes locally (or `pytest`)
- [ ] README updated (new QA/config option documented)
- [ ] CHANGELOG updated
