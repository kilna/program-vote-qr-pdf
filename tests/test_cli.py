import csv
from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfgen.canvas import Canvas

from program_vote_qr.cli import create_pdf, read_codes


def make_template(path: Path) -> None:
    canvas = Canvas(str(path), pagesize=(612, 792))
    canvas.drawString(72, 720, "Program back")
    canvas.save()


def make_codes(path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "used", "url"])
        writer.writeheader()
        writer.writerow({"code": "ABCD7", "used": "no", "url": "https://vote.sandiego48.com/c/ABCD7"})
        writer.writerow({"code": "EFGH8", "used": "yes", "url": "https://vote.sandiego48.com/c/EFGH8"})
        writer.writerow({"code": "JKLM9", "used": "no", "url": "https://vote.sandiego48.com/c/JKLM9"})


def test_read_codes_excludes_used_by_default(tmp_path: Path) -> None:
    codes = tmp_path / "codes.csv"
    make_codes(codes)
    assert [item.code for item in read_codes(codes)] == ["ABCD7", "JKLM9"]
    assert [item.code for item in read_codes(codes, include_used=True)] == ["ABCD7", "EFGH8", "JKLM9"]


def test_create_pdf_has_one_page_per_eligible_code(tmp_path: Path) -> None:
    template = tmp_path / "template.pdf"
    codes = tmp_path / "codes.csv"
    output = tmp_path / "output.pdf"
    make_template(template)
    make_codes(codes)

    eligible = read_codes(codes)
    create_pdf(template, eligible, output, x=450, y=72, size=90)

    reader = PdfReader(str(output))
    assert len(reader.pages) == 2
    assert float(reader.pages[0].mediabox.width) == 612
    assert float(reader.pages[0].mediabox.height) == 792
