"""Command-line interface for plansi."""

import atexit
import sys
from .control_codes import SHOW_CURSOR, RESTORE_TERMINAL
from .args import parse_args
from .pipeline import build_pipeline


def restore_cursor():
    """Restore cursor visibility on exit."""
    print(SHOW_CURSOR, end="", flush=True)


def main():
    """Main CLI entry point."""
    # Register cursor restoration for any exit scenario
    atexit.register(restore_cursor)

    # Parse arguments
    args = parse_args()

    try:
        # Build pipeline
        pipeline, is_file_output = build_pipeline(args)

        # Process pipeline
        for _ in pipeline:
            pass  # Pipeline handles output

        # Success message for file output
        if is_file_output:
            print(f"Wrote cast file: {args.output}", file=sys.stderr)

    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        print(RESTORE_TERMINAL, flush=True)
        sys.exit(0)
    except Exception:
        # Restore cursor on any error
        print(RESTORE_TERMINAL, flush=True)
        # Let the exception propagate with full stack trace
        raise
