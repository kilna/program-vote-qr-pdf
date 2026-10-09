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


def qr_overlay(page_width: float, page_height: float, vote: VoteCode, x: float, y: float, size: float, label: bool) -> bytes:
    if x < 0 or y < 0 or x + size > page_width or y + size > page_height:
        raise ValueError(
            f"QR at ({x}, {y}) with size {size} does not fit page "
            f"({page_width:g} x {page_height:g})"
        )
    if size <= 0:
        raise ValueError("QR size must be positive")

    qr = segno.make(vote.url, error="h")
    module_count = qr.symbol_size(scale=1)[0]
    module_size = size / module_count

    from io import BytesIO

    output = BytesIO()
    canvas = Canvas(output, pagesize=(page_width, page_height))
    canvas.setFillColorRGB(1, 1, 1)
    canvas.rect(x, y, size, size, fill=1, stroke=0)
    canvas.setFillColorRGB(0, 0, 0)
    matrix = qr.matrix
    for row_index, row in enumerate(matrix):
        for column_index, dark in enumerate(row):
            if dark:
                canvas.rect(
                    x + column_index * module_size,
                    y + (len(matrix) - 1 - row_index) * module_size,
                    module_size,
                    module_size,
                    fill=1,
                    stroke=0,
                )

    if label:
        canvas.setFont("Helvetica", max(6, min(12, size / 10)))
        canvas.drawCentredString(x + size / 2, max(2, y - size / 12), vote.code)
    canvas.save()
    return output.getvalue()


def create_pdf(
    template: Path,
    codes: list[VoteCode],
    output: Path,
    x: float,
    y: float,
    size: float,
    template_page: int = 0,
    label: bool = True,
) -> None:
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

    for vote in codes:
        overlay_reader = PdfReader(BytesIO(qr_overlay(width, height, vote, x, y, size, label)))
        # Load a fresh template page because merge_page mutates its target.
        page = PdfReader(str(template)).pages[template_page]
        writer.add_page(page)
        writer.pages[-1].merge_page(overlay_reader.pages[0])

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as handle:
        writer.write(handle)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, required=True, help="Source program-back PDF")
    parser.add_argument("--codes", type=Path, required=True, help="CSV downloaded from the voting admin")
    parser.add_argument("--output", type=Path, required=True, help="Output personalized PDF")
    parser.add_argument("--x", type=float, required=True, help="QR left position in PDF points")
    parser.add_argument("--y", type=float, required=True, help="QR bottom position in PDF points")
    parser.add_argument("--size", type=float, required=True, help="QR size in PDF points")
    parser.add_argument("--template-page", type=int, default=0, help="Zero-based source page to use")
    parser.add_argument("--include-used", action="store_true", help="Include codes marked used in the CSV")
    parser.add_argument("--no-label", action="store_true", help="Do not print the human-readable code below the QR")
    return parser


def main() -> None:
    args = parser().parse_args()
    if not args.template.exists():
        raise SystemExit(f"Template not found: {args.template}")
    if not args.codes.exists():
        raise SystemExit(f"Codes CSV not found: {args.codes}")
    try:
        codes = read_codes(args.codes, include_used=args.include_used)
        create_pdf(
            args.template,
            codes,
            args.output,
            args.x,
            args.y,
            args.size,
            template_page=args.template_page,
            label=not args.no_label,
        )
    except (OSError, ValueError) as error:
        raise SystemExit(str(error)) from error
    print(f"Created {args.output} with {len(codes)} personalized page(s).")


if __name__ == "__main__":
    main()
