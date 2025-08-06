"""Command-line interface for plansi."""

import atexit
import sys
from .control_codes import SHOW_CURSOR, RESTORE_TERMINAL
from .args import parse_args
from .pipeline import build_pipeline


def restore_cursor():
    """Restore cursor visibility on exit."""
    print(SHOW_CURSOR, end="", flush=True)


def _debug_args_and_pipeline(args, pipeline):
    """Print final resolved arguments and pipeline structure."""
    print("Final resolved arguments:")
    for key, value in sorted(vars(args).items()):
        if key == "debug_args":
            continue
        print(f"  {key}: {value!r}")

    print("\nPipeline structure:")
    _print_pipeline_tree(pipeline, 0)


def _print_pipeline_tree(pipe, level):
    """Print pipeline structure as a tree."""
    indent = "  " * level
    pipe_name = pipe.__class__.__name__
    print(f"{indent}{pipe_name}")

    # If this pipe has an input pipe, recurse
    if hasattr(pipe, "input") and pipe.input is not None:
        _print_pipeline_tree(pipe.input, level + 1)


def main():
    """Main CLI entry point."""
    # Register cursor restoration for any exit scenario
    atexit.register(restore_cursor)

    # Parse arguments
    args = parse_args()

    try:
        # Build pipeline
        pipeline, is_file_output = build_pipeline(args)

        # Debug args and pipeline if requested
        if args.debug_args:
            _debug_args_and_pipeline(args, pipeline)
            sys.exit(0)

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
