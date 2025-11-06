## arch-me-later CLI

This project uses Typer to provide a multi-command CLI.

### Run

```
uv run archme --help
uv run archme tui
uv run archme logs -f
```

You can also run the module directly:

```
uv run python -m arch_me_later.cli --help
```

### Add new commands

Edit `src/arch_me_later/cli.py` and add functions decorated with `@app.command()`:

```python
@app.command()
def sync(force: bool = typer.Option(False, "--force")):
	"""Synchronize data."""
	...
```

The console script `archme` is configured in `pyproject.toml`:

```
[project.scripts]
archme = "arch_me_later.cli:app"
```

