"""Entrypoint for graph_rag CLI."""

from .app import run_cli


def main() -> None:
    """CLI entry point used by `python -m graph_rag.main`."""

    run_cli()


if __name__ == "__main__":
    main()