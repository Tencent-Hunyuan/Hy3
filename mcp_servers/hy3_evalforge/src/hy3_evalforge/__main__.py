"""Console entry point for the Hy3 EvalForge stdio MCP server."""


def main() -> None:
    """Start the server without emitting non-protocol data to stdout."""
    from hy3_evalforge.server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
