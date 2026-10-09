from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen.canvas import Canvas
import segno


@dataclass(frozen=True)
class VoteCode:
    code: str
    url: str
    used: bool


@dataclass(frozen=True)
class Placement:
    x: float
    y: float
    size: float


def parse_placement(value: str) -> Placement:
    try:
        x, y, size = (float(part.strip()) for part in value.split(","))
    except ValueError as error:
        raise ValueError(f"Placement must be X,Y,SIZE; got {value!r}") from error
    if size <= 0:
        raise ValueError("QR size must be positive")
    return Placement(x=x, y=y, size=size)


def read_codes(path: Path, include_used: bool = False) -> list[VoteCode]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = csv.DictReader(handle)
        required = {"code", "url"}
        missing = required - set(rows.fieldnames or [])
        if missing:
            raise ValueError(f"CSV is missing required columns: {', '.join(sorted(missing))}")

        result: list[VoteCode] = []
        for row_number, row in enumerate(rows, start=2):
            code = (row.get("code") or "").strip()
            url = (row.get("url") or "").strip()
            used = (row.get("used") or "").strip().lower() in {"yes", "true", "1"}
            if not code or not url:
                raise ValueError(f"CSV row {row_number} must contain both code and url")
            if include_used or not used:
                result.append(VoteCode(code=code, url=url, used=used))

    if not result:
        raise ValueError("No eligible vote codes found")
    return result


def qr_overlay(page_width: float, page_height: float, vote: VoteCode, placement: Placement, ballot_number: int, label: bool) -> bytes:
    x, y, size = placement.x, placement.y, placement.size
    label_height = max(18, size / 5) if label else 0
    if x < 0 or y - label_height < 0 or x + size > page_width or y + size > page_height:
        raise ValueError(
            f"QR at ({x}, {y}) with size {size} does not fit page "
            f"({page_width:g} x {page_height:g})"
        )

    qr = segno.make(vote.url, error="h")
    # Segno's matrix excludes the QR quiet zone. Reserve the standard four
    # light modules on every side so printed codes remain easy to scan.
    matrix = qr.matrix
    module_count = len(matrix) + 8
    module_size = size / module_count

    from io import BytesIO

    output = BytesIO()
    canvas = Canvas(output, pagesize=(page_width, page_height))
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(x, y, size, size, fill=1, stroke=0)
    canvas.setFillColorRGB(0, 0, 0)
    for row_index, row in enumerate(matrix):
        for column_index, dark in enumerate(row):
            if dark:
                canvas.rect(
                    x + (column_index + 4) * module_size,
                    y + (len(matrix) - row_index + 3) * module_size,
                    module_size,
                    module_size,
                    fill=1,
                    stroke=0,
                )

    if label:
        font_size = max(6, min(11, size / 10))
        canvas.setFont("Helvetica-Bold", font_size)
        canvas.drawCentredString(x + size / 2, y - font_size - 2, f"Ballot {ballot_number:03d}")
        canvas.setFont("Helvetica", font_size)
        canvas.drawCentredString(x + size / 2, y - (font_size * 2) - 4, f"Code: {vote.code}")
    canvas.save()
    return output.getvalue()


def create_pdf(
    template: Path,
    codes: list[VoteCode],
    output: Path,
    placements: list[Placement],
    template_page: int = 0,
    label: bool = True,
    start_ballot_number: int = 1,
) -> None:
    if not placements:
        raise ValueError("At least one placement is required")
    if start_ballot_number < 1:
        raise ValueError("Starting ballot number must be positive")
    source = PdfReader(str(template))
    if not source.pages:
        raise ValueError("Template PDF has no pages")
    if template_page < 0 or template_page >= len(source.pages):
        raise ValueError(f"Template page must be between 0 and {len(source.pages) - 1}")

    template_page_object = source.pages[template_page]
    box = template_page_object.mediabox
    width = float(box.width)
    height = float(box.height)
    writer = PdfWriter()

    from io import BytesIO

    for page_start in range(0, len(codes), len(placements)):
        page_codes = codes[page_start:page_start + len(placements)]
        # Load a fresh template page because merge_page mutates its target.
        page = PdfReader(str(template)).pages[template_page]
        writer.add_page(page)
        for slot, vote in enumerate(page_codes):
            ballot_number = start_ballot_number + page_start + slot
            overlay_reader = PdfReader(BytesIO(qr_overlay(width, height, vote, placements[slot], ballot_number, label)))
            writer.pages[-1].merge_page(overlay_reader.pages[0])

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True, help="Source program-back PDF")
    parser.add_argument("--codes", type=Path, required=True, help="CSV downloaded from the voting admin")
    parser.add_argument("--output", type=Path, required=True, help="Output personalized PDF")
    parser.add_argument(
        "--placement",
        action="append",
        metavar="X,Y,SIZE",
        required=True,
        help="QR placement in PDF points; repeat for each slot on a template page",
    )
    parser.add_argument("--template-page", type=int, default=0, help="Zero-based source page to use")
    parser.add_argument("--include-used", action="store_true", help="Include codes marked used in the CSV")
    parser.add_argument("--no-label", action="store_true", help="Do not print the human-readable code below the QR")
    parser.add_argument("--start-ballot-number", type=int, default=1, help="Number printed on the first ballot")
    return parser


def main() -> None:
    args = parser().parse_args()
    if not args.template.exists():
        raise SystemExit(f"Template not found: {args.template}")
    if not args.codes.exists():
        raise SystemExit(f"Codes CSV not found: {args.codes}")
    try:
        codes = read_codes(args.codes, include_used=args.include_used)
        placements = [parse_placement(value) for value in args.placement]
        create_pdf(
            args.template,
            codes,
            args.output,
            placements,
            template_page=args.template_page,
            label=not args.no_label,
            start_ballot_number=args.start_ballot_number,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    pages = (len(codes) + len(placements) - 1) // len(placements)
    print(f"Created {args.output} with {len(codes)} ballot(s) on {pages} page(s).")


if __name__ == "__main__":
    main()
