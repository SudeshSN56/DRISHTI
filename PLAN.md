# Drone Surveillance Report System Plan

## Product scope

Local Windows 11 Streamlit app for recorded MP4, AVI, or MOV clips. Uses a
pretrained COCO YOLO model with ByteTrack; no model training, database, login,
cloud processing, GPS, live drone input, or thermal/night processing.

The run CSV is the source of truth for counts, timeline, charts, summary, and
PDF. Generate the PDF only after the user clicks **Print Brief**. The annotated
video is the only result that cannot be reconstructed from the CSV.

## Implementation phases

- **0 — Setup:** Python 3.12 venv, CUDA PyTorch, dependencies, app folders.
- **0.5 — Demo data:** keep manually downloaded VisDrone-VID validation data
  under ignored `datasets/`; stitch numbered JPG sequence folders into MP4
  clips in ignored `test_videos/` using `tools.frames_to_video`.
- **1 — Pipeline:** validate video input; use GPU YOLO/ByteTrack, selected model
  classes, five-frame track minimum, CSV/snapshots, H.264 output, progress, and
  optional downscaled annotated-frame/live-count callback.
- **2 — Analysis:** derive counts, timeline, chart data, and template summary
  from CSV only.
- **3 — UI:** upload and class selection, progress and live preview/counts,
  CSV-derived results, CSV/PDF downloads, video and snapshots, clear errors.
- **4 — Brief:** build a PDF from the selected run's CSV and available
  snapshots only when the user clicks **Print Brief**.
- **5 — Testing:** automated synthetic cases plus real traffic/crowd, empty,
  corrupt, five-minute, high-altitude, and edited-class tests when clips are
  available; report real GPU processing speed.
- **6 — Demo:** Windows setup/run instructions, known limitations, two clean
  start-to-finish rehearsals.

## Current status

Phases 0–6 are implemented. The revised frame-folder converter and live preview
are covered by automated tests; three VisDrone-VID validation sequences have
been converted and run through the CUDA pipeline. The official archive is kept
locally under ignored `datasets/`, with generated clips in ignored
`test_videos/` and results in ignored `outputs/`.

Sampled annotated frames from all three clips and representative saved crops
were visually checked; crop usefulness varies for distant or partially visible
objects. This qualitative review is not an accuracy evaluation. Remaining
real-footage work: compare predictions against suitable VisDrone ground-truth
annotations, measure memory on real 1080p stress footage, and test high-altitude
and separate stock clips if available. No VisDrone video/annotation data should
be committed or redistributed without confirming the provider's terms.

## UI redesign

The `ui-redesign` branch replaces the single-page Streamlit interface with a
graphite command console. UI modules provide shared theme/components, pure SVG
charts, CSV-derived run filtering and object dossiers, and Analyze, Results,
Run Explorer, and Object Dossier pages. No pipeline behavior or CSV schema is
changed. Processing throughput remains unavailable because it is not recorded
in the existing CSV.
