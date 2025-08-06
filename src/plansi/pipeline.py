"""Pipeline building for plansi."""

import os
from .pipe import VideoReader, ImageToAnsi, CastWriter, CastReader, AnsiBuffer, FileWriter, TerminalPlayer


def get_input(args):
    """Create input pipeline based on input file type.

    Args:
        args: Parsed command-line arguments

    Returns:
        Pipe: Input pipeline (CastReader or VideoReader -> ImageToAnsi)
    """
    # Create input list for source pipe
    input_list = [(0.0, args.input)]

    # Determine input type and create appropriate reader
    if args.input.endswith(".cast"):
        # Cast file input
        return CastReader(input_list, args)
    else:
        # Video file input - convert to ANSI
        video = VideoReader(input_list, args)
        return ImageToAnsi(video, args)


def get_processor(input_pipe, args):
    """Apply processing stages to the input pipeline.

    Args:
        input_pipe: Input pipeline
        args: Parsed command-line arguments

    Returns:
        Pipe: Processed pipeline
    """
    pipeline = input_pipe

    # Apply differential rendering unless disabled
    if not args.no_diff:
        pipeline = AnsiBuffer(pipeline, args)

    return pipeline


def get_output(processor, args):
    """Create output pipeline based on output destination.

    Args:
        processor: Processed pipeline
        args: Parsed command-line arguments

    Returns:
        tuple: (pipeline, is_output_to_file) where pipeline is the final pipe to iterate
    """
    if args.stdout:
        # Play to terminal
        pipeline = TerminalPlayer(processor, args)
        return pipeline, False
    else:
        # Output to .cast file
        is_cast_input = args.input.endswith(".cast")

        if not is_cast_input:
            # Need to convert ANSI to cast format
            args.title = f"plansi - {os.path.basename(args.input)}"
            cast = CastWriter(processor, args)
            pipeline = FileWriter(cast, args)
        else:
            # Direct copy of cast file - no title needed
            pipeline = FileWriter(processor, args)

        return pipeline, True


def build_pipeline(args):
    """Build the complete processing pipeline.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (pipeline, is_output_to_file) where pipeline is the final pipe to iterate
    """
    input_pipe = get_input(args)
    processor = get_processor(input_pipe, args)
    return get_output(processor, args)
