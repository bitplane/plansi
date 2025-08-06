"""Pipeline building for plansi."""

import os
from .pipe import VideoReader, ImageToAnsi, CastWriter, CastReader, AnsiBuffer, FileWriter, TerminalPlayer


def build_pipeline(args):
    """Build the processing pipeline based on input/output arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (pipeline, is_output_to_file) where pipeline is the final pipe to iterate
    """
    # Determine input type
    is_cast_input = args.input.endswith(".cast")

    # Create input list for source pipe
    input_list = [(0.0, args.input)]

    # Build input pipeline
    if is_cast_input:
        # Cast file input - play or convert
        pipeline = CastReader(input_list, args)
    else:
        # Video file input - convert to ANSI
        video = VideoReader(input_list, args)
        pipeline = ImageToAnsi(video, args)

    # Apply differential rendering unless disabled
    if not args.no_diff:
        pipeline = AnsiBuffer(pipeline, args)

    # Build output pipeline
    if args.output:
        # Output to .cast file
        if not is_cast_input:
            # Need to convert ANSI to cast format
            args.title = f"plansi - {os.path.basename(args.input)}"
            cast = CastWriter(pipeline, args)
            pipeline = FileWriter(cast, args)
        else:
            # Direct copy of cast file - no title needed
            pipeline = FileWriter(pipeline, args)
        return pipeline, True
    else:
        # Play to terminal
        args.realtime = True
        pipeline = TerminalPlayer(pipeline, args)
        return pipeline, False
