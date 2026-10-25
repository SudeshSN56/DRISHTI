export interface CountItem {
  class_name: string;
  count: number;
}

export interface TimelineItem {
  bucket_start_sec: number;
  bucket_end_sec: number;
  class_name: string;
  count: number;
}

export interface SnapshotItem {
  track_id: string;
  class_name: string;
  first_seen_sec: number;
  last_seen_sec: number;
  avg_confidence: number | null;
  path: string | null;
}

export interface RunSummary {
  id: string;
  video_name: string;
  processed_at: string;
  duration_sec: number;
  total_objects: number;
  classes: string[];
  location: string | null;
  has_annotated_video: boolean;
  has_brief: boolean;
}

export interface RunDetail {
  id: string;
  video_name: string;
  processed_at: string;
  duration_sec: number;
  summary: string;
  counts: CountItem[];
  timeline: TimelineItem[];
  visible_timeline: TimelineItem[];
  fps: number | null;
  processing_fps: number | null;
  model: string | null;
  confidence: number | null;
  imgsz: number | null;
  min_track_frames: number | null;
  min_box_px: number | null;
  processing_seconds: number | null;
  device: string | null;
  location: string | null;
  confidence_overrides: string | null;
  snapshots: SnapshotItem[];
  has_annotated_video: boolean;
  has_brief: boolean;
}

export interface ModelInfo {
  model_name: string;
  default_classes: string[];
  all_classes: string[];
  cuda_available: boolean;
  device_name: string | null;
  confidence_threshold: number;
  image_size: number;
  min_track_frames: number;
  min_box_px: number;
  max_inference_width: number;
  half_precision: boolean;
}

export interface SampleVideo {
  name: string;
  path: string;
  size_mb: number;
}

export type DetectSSEEvent =
  | {
      type: 'progress';
      processed: number;
      total: number;
      percent: number;
      fps: number;
      elapsed: number;
    }
  | {
      type: 'preview';
      frame: string;
      counts: Record<string, number>;
    }
  | {
      type: 'complete';
      run_id: string;
      summary: string;
      elapsed: number;
    }
  | {
      type: 'error';
      message: string;
    };
