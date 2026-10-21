from dataclasses import dataclass
import math
from pathlib import Path

import cv2


class VideoSourceError(ValueError):
    """Raised when a video cannot be opened or read."""


@dataclass(frozen=True)
class VideoMetadata:
    path: Path
    fps: float
    frame_count: int
    width: int
    height: int

    @property
    def duration_sec(self) -> float:
        return self.frame_count / self.fps


class VideoSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.is_file():
            raise VideoSourceError(f"Video file does not exist: {self.path}")

        self.capture = cv2.VideoCapture(str(self.path))
        if not self.capture.isOpened():
            self.capture.release()
            raise VideoSourceError(f"OpenCV could not open video: {self.path}")

        fps = self.capture.get(cv2.CAP_PROP_FPS)
        frame_count = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not math.isfinite(fps) or fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
            self.capture.release()
            raise VideoSourceError(f"Video has invalid metadata or is unsupported: {self.path}")

        readable, _ = self.capture.read()
        if not readable:
            self.capture.release()
            raise VideoSourceError(f"Video contains no readable frames: {self.path}")
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.metadata = VideoMetadata(self.path, fps, frame_count, width, height)

    def read(self):
        return self.capture.read()

    def close(self) -> None:
        self.capture.release()

    def __enter__(self) -> "VideoSource":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
