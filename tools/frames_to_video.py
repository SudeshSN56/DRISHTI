import argparse
import math
from pathlib import Path
import re
import sys

import cv2
from imageio_ffmpeg import write_frames


IMAGE_SUFFIXES = {".jpg", ".jpeg"}


def _natural_sort_key(path: Path) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )


def _sequence_directories(root: Path) -> list[Path]:
    directories = [
        directory
        for directory in (root, *root.rglob("*"))
        if directory.is_dir()
        and any(
            child.is_file() and child.suffix.lower() in IMAGE_SUFFIXES
            for child in directory.iterdir()
        )
    ]
    return sorted(directories, key=lambda directory: _natural_sort_key(directory.relative_to(root)))


def _output_name(root: Path, sequence_dir: Path) -> str:
    relative = sequence_dir.relative_to(root)
    parts = relative.parts or (root.name,)
    safe_parts = [
        re.sub(r"[^A-Za-z0-9_-]+", "_", part).strip("_") or "sequence"
        for part in parts
    ]
    return "_".join(safe_parts) + ".mp4"


def stitch_sequence(
    sequence_dir: str | Path,
    output_path: str | Path,
    fps: float = 30.0,
) -> Path:
    """Stitch the numbered JPG frames in a directory into an H.264 MP4."""
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("FPS must be a positive finite number.")
    frame_dir = Path(sequence_dir)
    if not frame_dir.is_dir():
        raise NotADirectoryError(f"Frame sequence directory does not exist: {frame_dir}")

    frame_paths = sorted(
        (
            path
            for path in frame_dir.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        ),
        key=_natural_sort_key,
    )
    if not frame_paths:
        raise ValueError(f"No JPG/JPEG frames found in {frame_dir}")

    first_frame = cv2.imread(str(frame_paths[0]))
    if first_frame is None:
        raise ValueError(f"Could not read image frame: {frame_paths[0]}")
    height, width = first_frame.shape[:2]
    if width <= 0 or height <= 0:
        raise ValueError(f"Frame has invalid dimensions: {frame_paths[0]}")

    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing video: {target}")
    writer = write_frames(
        target,
        (width + width % 2, height + height % 2),
        fps=fps,
        codec="libx264",
        macro_block_size=1,
        output_params=["-movflags", "+faststart"],
    )
    writer.send(None)

    try:
        for frame_path in frame_paths:
            frame = cv2.imread(str(frame_path))
            if frame is None:
                raise ValueError(f"Could not read image frame: {frame_path}")
            if frame.shape[:2] != (height, width):
                raise ValueError(
                    f"Inconsistent frame dimensions in {frame_dir}: "
                    f"{frame_path.name} is {frame.shape[1]}x{frame.shape[0]}, "
                    f"expected {width}x{height}."
                )
            if width % 2 or height % 2:
                frame = cv2.copyMakeBorder(
                    frame,
                    0,
                    height % 2,
                    0,
                    width % 2,
                    cv2.BORDER_CONSTANT,
                    value=(0, 0, 0),
                )
            writer.send(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    except (OSError, ValueError, RuntimeError, cv2.error):
        writer.close()
        target.unlink(missing_ok=True)
        raise
    else:
        writer.close()
    return target


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stitch numbered JPG frame sequences into H.264 MP4 clips."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="A frame-sequence directory or its parent directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_videos"),
        help="Directory for generated MP4 files (default: test_videos).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=30.0,
        help="Frames per second (default: 30; use the dataset's value when known).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stitch only the first N sequences (0 means all).",
    )
    args = parser.parse_args()

    if not args.input.is_dir():
        parser.error(f"Input directory does not exist: {args.input}")
    if not math.isfinite(args.fps) or args.fps <= 0:
        parser.error("--fps must be a positive finite number.")
    if args.limit < 0:
        parser.error("--limit cannot be negative.")

    sequence_dirs = _sequence_directories(args.input)
    if args.limit:
        sequence_dirs = sequence_dirs[: args.limit]
    if not sequence_dirs:
        print(f"No directories containing JPG frames found under {args.input}", file=sys.stderr)
        return 1

    for sequence_dir in sequence_dirs:
        output_path = args.output / _output_name(args.input, sequence_dir)
        try:
            stitch_sequence(sequence_dir, output_path, args.fps)
        except (OSError, ValueError, RuntimeError) as error:
            print(f"Error processing {sequence_dir}: {error}", file=sys.stderr)
            return 1
        print(f"Created {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
