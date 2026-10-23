from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
TEST_VIDEOS_DIR = PROJECT_ROOT / "test_videos"

MODEL_NAME = "yolo11s.pt"
CONFIDENCE_THRESHOLD = 0.35
IMAGE_SIZE = 960
MIN_TRACK_FRAMES = 5
MIN_BOX_PX = 0
MAX_INFERENCE_WIDTH = 0
HALF_PRECISION = False
CLASS_CONFIDENCE_OVERRIDES: dict[str, float] = {}
TRACKER_CONFIG_PATH = PROJECT_ROOT / "core" / "bytetrack.yaml"
TIMELINE_BUCKET_SECONDS = 5

DEFAULT_CLASSES = (
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "boat",
    "bird",
    "dog",
    "cat",
    "horse",
    "cow",
    "sheep",
)
