from __future__ import annotations
import typer
from arch_me_later.tui import run as run_tui

app = typer.Typer(help="arch-me-later command line interface", no_args_is_help=True)


@app.command()
def tui() -> None:
    """Launch the Textual TUI (placeholder)."""
    run_tui()


@app.command()
def logs(
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Follow log output (like tail -f)",
    ),
) -> None:
    """Show application logs (placeholder)."""
    if follow:
        typer.echo("Following logs... (Ctrl+C to stop)")
    else:
        typer.echo("Showing logs once...")


if __name__ == "__main__":
    app()
