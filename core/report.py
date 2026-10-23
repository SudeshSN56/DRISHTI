import colorsys
import re
from io import BytesIO
from pathlib import Path

import matplotlib
import pandas as pd
from fpdf import FPDF
from PIL import Image

from core.analysis import AnalysisResult, analyze_csv
from ui.components import class_color


matplotlib.use("Agg")

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure


SNAPSHOTS_PER_CLASS = 3


class _BriefPDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("DejaVu", size=8)
        self.set_text_color(110, 113, 119)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="R")


def _class_rgb(class_name: str) -> tuple[int, int, int]:
    color = class_color(class_name)
    if color.startswith("#"):
        return tuple(int(color[index : index + 2], 16) for index in (1, 3, 5))
    match = re.fullmatch(r"hsl\((\d+) 58% 62%\)", color)
    if not match:
        raise ValueError(f"Unsupported class color format for {class_name!r}: {color}")
    hue = int(match.group(1)) / 360
    red, green, blue = colorsys.hls_to_rgb(hue, 0.62, 0.58)
    return round(red * 255), round(green * 255), round(blue * 255)


def _paragraph(pdf: FPDF, height: float, text: str) -> None:
    pdf.multi_cell(
        0,
        height,
        text,
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _format_duration(seconds: float) -> str:
    minutes = int(seconds) // 60
    remaining_seconds = seconds - minutes * 60
    return f"{minutes}:{remaining_seconds:05.2f}"


def _chart_image(counts: pd.DataFrame, timeline: pd.DataFrame, chart_type: str) -> BytesIO:
    figure = Figure(figsize=(9, 4.5), tight_layout=True)
    canvas = FigureCanvasAgg(figure)
    axis = figure.subplots()

    if chart_type == "counts":
        if counts.empty:
            axis.text(0.5, 0.5, "No objects detected", ha="center", va="center")
            axis.set_axis_off()
        else:
            ordered_counts = counts.sort_values("count", ascending=True)
            axis.barh(
                ordered_counts["class"],
                ordered_counts["count"],
                color=[_class_hex(name) for name in ordered_counts["class"]],
            )
            axis.set_xlabel("Unique tracked objects")
            axis.set_title("Objects by class")
            axis.grid(axis="x", alpha=0.2)
    else:
        if timeline.empty:
            axis.text(0.5, 0.5, "No timeline data", ha="center", va="center")
            axis.set_axis_off()
        else:
            for class_name, class_timeline in timeline.groupby("class"):
                labels = [
                    f"{int(start // 60)}:{int(start % 60):02d}"
                    for start in class_timeline["bucket_start_sec"]
                ]
                axis.plot(
                    labels,
                    class_timeline["count"],
                    marker="o",
                    label=class_name,
                    color=_class_hex(class_name),
                )
            axis.set_xlabel("First-seen time window")
            axis.set_ylabel("Unique objects")
            axis.set_title("New objects first seen per 5-second window")
            axis.grid(alpha=0.2)
            if timeline["class"].nunique() > 1:
                axis.legend(loc="best")
            figure.autofmt_xdate(rotation=30)

    image = BytesIO()
    canvas.print_png(image)
    image.seek(0)
    return image


def _class_hex(class_name: str) -> str:
    return "#" + "".join(f"{component:02x}" for component in _class_rgb(class_name))


def _snapshot_paths(csv_path: Path) -> tuple[dict[str, list[Path]], int]:
    run_dir = csv_path.parent.resolve()
    detections = pd.read_csv(csv_path)
    if "snapshot_path" not in detections.columns:
        return {}, 0

    snapshots: dict[str, list[tuple[float, Path]]] = {}
    missing = 0
    snapshot_rows = detections.loc[
        detections["class"].notna() & detections["class"].ne("__none__"),
        ["class", "snapshot_path", "avg_confidence"],
    ]
    for class_name, relative_path, confidence in snapshot_rows.itertuples(
        index=False,
        name=None,
    ):
        if not isinstance(relative_path, str) or not relative_path.strip():
            continue
        snapshot = (run_dir / relative_path).resolve()
        try:
            snapshot.relative_to(run_dir)
        except ValueError as error:
            raise ValueError("A snapshot path in the CSV points outside its run folder.") from error
        if not snapshot.is_file():
            missing += 1
            continue
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        snapshots.setdefault(str(class_name), []).append((confidence, snapshot))

    selected = {
        class_name: [
            path
            for _, path in sorted(paths, key=lambda item: item[0], reverse=True)[
                :SNAPSHOTS_PER_CLASS
            ]
        ]
        for class_name, paths in snapshots.items()
    }
    return selected, missing


def _write_brief(
    pdf_path: Path,
    analysis: AnalysisResult,
    counts_chart: BytesIO,
    timeline_chart: BytesIO,
    snapshots: dict[str, list[Path]],
    missing_snapshots: int,
) -> None:
    pdf = _BriefPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.alias_nb_pages()
    pdf.add_font(
        "DejaVu",
        "",
        str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf"),
    )
    pdf.add_page()
    pdf.set_font("DejaVu", size=19)
    _paragraph(pdf, 11, "Drone Surveillance Brief")
    pdf.ln(2)

    pdf.set_font("DejaVu", size=10)
    _paragraph(pdf, 6, f"Video: {analysis.video_name}")
    _paragraph(pdf, 6, f"Duration: {_format_duration(analysis.video_duration_sec)}")
    _paragraph(pdf, 6, f"Processed: {analysis.processed_at}")
    pdf.ln(4)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Run settings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=9)
    run_settings = (
        ("Model", analysis.model),
        (
            "Confidence",
            f"{analysis.confidence:.2f}" if analysis.confidence is not None else None,
        ),
        ("Image size", f"{analysis.imgsz}px" if analysis.imgsz is not None else None),
        (
            "Minimum track length",
            f"{analysis.min_track_frames} frames"
            if analysis.min_track_frames is not None else None,
        ),
        (
            "Processing time",
            f"{analysis.processing_seconds:.2f}s"
            if analysis.processing_seconds is not None else None,
        ),
        ("Device", analysis.device),
        ("Location", analysis.location),
    )
    for label, value in run_settings:
        _paragraph(pdf, 5, f"{label}: {value or 'Not recorded'}")
    pdf.ln(2)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Class colour legend", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=8)
    classes = analysis.counts["class"].astype(str).tolist()
    for index, class_name in enumerate(classes):
        column = index % 3
        if column == 0:
            if pdf.will_page_break(7):
                pdf.add_page()
            row_y = pdf.get_y()
        x = pdf.l_margin + column * 62
        pdf.set_fill_color(*_class_rgb(class_name))
        pdf.rect(x, row_y + 1.5, 3.5, 3.5, style="F")
        pdf.set_xy(x + 5, row_y)
        pdf.cell(55, 7, class_name)
        if column == 2 or index == len(classes) - 1:
            pdf.set_y(row_y + 7)
    if classes:
        pdf.ln(2)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Unique tracked object counts", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=10)
    if analysis.counts.empty:
        _paragraph(pdf, 7, "No objects detected.")
    else:
        pdf.set_fill_color(230, 237, 247)
        pdf.cell(105, 8, "Class", border=1, fill=True)
        pdf.cell(45, 8, "Unique tracks", border=1, fill=True, new_x="LMARGIN", new_y="NEXT")
        for row in analysis.counts.itertuples(index=False):
            pdf.cell(105, 8, str(row[0]), border=1)
            pdf.cell(45, 8, str(int(row[1])), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Counts chart", new_x="LMARGIN", new_y="NEXT")
    pdf.image(counts_chart, w=175)
    pdf.ln(3)
    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Timeline chart", new_x="LMARGIN", new_y="NEXT")
    pdf.image(timeline_chart, w=175)
    pdf.ln(3)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=10)
    _paragraph(pdf, 6, analysis.summary)
    pdf.ln(3)

    pdf.set_font("DejaVu", size=13)
    pdf.cell(0, 9, "Object snapshots", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("DejaVu", size=10)
    if snapshots:
        for class_name, class_snapshots in snapshots.items():
            pdf.set_font("DejaVu", size=11)
            pdf.cell(0, 8, class_name, new_x="LMARGIN", new_y="NEXT")
            for row_start in range(0, len(class_snapshots), 3):
                row_snapshots = class_snapshots[row_start : row_start + 3]
                row_y = pdf.get_y()
                if row_y > 245:
                    pdf.add_page()
                    row_y = pdf.get_y()
                image_height = 0.0
                for column, snapshot in enumerate(row_snapshots):
                    with Image.open(snapshot) as image:
                        width, height = image.size
                    scale = min(50.0 / width, 35.0 / height)
                    display_width = width * scale
                    display_height = height * scale
                    image_x = pdf.l_margin + column * 58
                    pdf.image(
                        str(snapshot),
                        x=image_x,
                        y=row_y,
                        w=display_width,
                        h=display_height,
                    )
                    image_height = max(image_height, display_height)
                pdf.set_y(row_y + image_height + 4)
    else:
        _paragraph(pdf, 6, "No saved object snapshots are available.")
    if missing_snapshots:
        pdf.ln(2)
        _paragraph(
            pdf,
            6,
            f"{missing_snapshots} snapshot file(s) listed in the CSV were unavailable.",
        )

    pdf.ln(4)
    pdf.set_font("DejaVu", size=9)
    _paragraph(
        pdf,
        5,
        "Limitations: small objects at altitude may be missed. Counts are approximate; "
        "tracking can split one object into multiple IDs or merge different objects.",
    )
    pdf.output(str(pdf_path))


def build_brief(csv_path: str | Path) -> Path:
    """Create a PDF brief from a run CSV and its optional snapshot images."""
    source = Path(csv_path)
    analysis = analyze_csv(source)
    snapshots, missing_snapshots = _snapshot_paths(source)
    pdf_path = source.parent / "brief.pdf"

    counts_chart = _chart_image(analysis.counts, analysis.timeline, "counts")
    timeline_chart = _chart_image(analysis.counts, analysis.timeline, "timeline")
    _write_brief(
        pdf_path,
        analysis,
        counts_chart,
        timeline_chart,
        snapshots,
        missing_snapshots,
    )
    return pdf_path
