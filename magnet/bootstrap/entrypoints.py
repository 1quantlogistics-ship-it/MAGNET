"""
bootstrap/entrypoints.py - Application entry points v1.1

Module 55: Bootstrap Layer

Provides CLI, API, and Worker entry points.
"""

from __future__ import annotations
from typing import Optional
import argparse
import logging
import sys
import os

logger = logging.getLogger("bootstrap.entrypoints")


def setup_logging(level: str = "INFO", log_file: str = None, json_format: bool = False) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        json_format: Use JSON format for logs
    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if json_format:
        try:
            import json

            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    return json.dumps({
                        "timestamp": self.formatTime(record),
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    })

            formatter = JSONFormatter()
        except Exception:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def cli_main(args: list = None) -> int:
    """
    CLI entry point.

    Args:
        args: Command line arguments (defaults to sys.argv)

    Returns:
        Exit code
    """
    parser = argparse.ArgumentParser(
        description="MAGNET Ship Design System CLI",
        prog="magnet",
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )
    parser.add_argument(
        "--log-file",
        help="Log file path",
        default=None,
    )
    parser.add_argument(
        "-s", "--script",
        help="Execute script file",
        default=None,
    )
    parser.add_argument(
        "-e", "--execute",
        help="Execute single command",
        default=None,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    parsed = parser.parse_args(args)

    # Setup logging
    log_level = "DEBUG" if parsed.verbose else parsed.log_level
    setup_logging(level=log_level, log_file=parsed.log_file)

    try:
        from .app import MAGNETApp

        app = MAGNETApp(parsed.config)

        if parsed.script:
            # Execute script file
            app.build()
            from magnet.cli.repl import REPL
            from magnet.cli.core import CLIContext

            ctx = CLIContext()
            try:
                from magnet.core.state_manager import StateManager
                ctx.state = app.container.resolve(StateManager)
            except Exception:
                pass

            repl = REPL(ctx)
            results = repl.execute_file(parsed.script)
            return 0 if all(r.success for r in results) else 1

        elif parsed.execute:
            # Execute single command
            app.build()
            from magnet.cli.repl import REPL
            from magnet.cli.core import CLIContext, format_output

            ctx = CLIContext()
            try:
                from magnet.core.state_manager import StateManager
                ctx.state = app.container.resolve(StateManager)
            except Exception:
                pass

            repl = REPL(ctx)
            result = repl.execute_line(parsed.execute)
            print(format_output(result, ctx.output_format))
            return result.exit_code

        else:
            # Interactive mode
            return app.run_cli()

    except KeyboardInterrupt:
        print("\nInterrupted")
        return 130
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


def api_main(args: list = None) -> None:
    """
    API server entry point.

    Args:
        args: Command line arguments
    """
    parser = argparse.ArgumentParser(
        description="MAGNET API Server",
        prog="magnet-api",
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        help="API port",
        default=None,
    )
    parser.add_argument(
        "-H", "--host",
        help="API host",
        default=None,
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        help="Number of workers",
        default=None,
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development)",
    )

    parsed = parser.parse_args(args)

    # Setup logging
    setup_logging(level=parsed.log_level)

    try:
        from .app import MAGNETApp
        from .config import load_config

        app = MAGNETApp(parsed.config)
        app.build()

        # Override config with CLI args
        if parsed.port:
            app.config.api.port = parsed.port
        if parsed.host:
            app.config.api.host = parsed.host
        if parsed.workers:
            app.config.api.workers = parsed.workers

        app.run_api()

    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


def run_worker(args: list = None) -> None:
    """
    Background worker entry point.

    Args:
        args: Command line arguments
    """
    parser = argparse.ArgumentParser(
        description="MAGNET Background Worker",
        prog="magnet-worker",
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "-n", "--concurrency",
        type=int,
        help="Worker concurrency",
        default=4,
    )
    parser.add_argument(
        "-q", "--queue",
        help="Queue name",
        default="default",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )

    parsed = parser.parse_args(args)

    # Setup logging
    setup_logging(level=parsed.log_level)

    try:
        from .app import MAGNETApp

        app = MAGNETApp(parsed.config)
        app.run_worker(concurrency=parsed.concurrency)

    except KeyboardInterrupt:
        print("\nShutting down worker...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


def main():
    """Main entry point for the package."""
    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "api":
            api_main(sys.argv[2:])
        elif command == "worker":
            run_worker(sys.argv[2:])
        elif command == "cli":
            sys.exit(cli_main(sys.argv[2:]))
        elif command in ["-h", "--help"]:
            print("MAGNET Ship Design System v1.1.0")
            print()
            print("Usage: python -m magnet.bootstrap.entrypoints <command> [options]")
            print()
            print("Commands:")
            print("  cli      Start interactive CLI")
            print("  api      Start API server")
            print("  worker   Start background worker")
            print()
            print("Use '<command> --help' for command-specific help.")
        else:
            # Default to CLI with args
            sys.exit(cli_main(sys.argv[1:]))
    else:
        # Default to interactive CLI
        sys.exit(cli_main([]))


if __name__ == "__main__":
    main()
