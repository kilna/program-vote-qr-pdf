# Program Vote QR PDF

Create a print-ready PDF with one unique voting QR code overlaid on each copy of a source program-back PDF.

This is intentionally a local tool. It consumes the CSV downloaded from the `vote-sandiego48.com` admin page and does not need access to the voting database or admin credentials.

## Setup

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
```

## Usage

The voting admin's CSV has `code`, `used`, and `url` columns. By default, used codes are excluded:

```sh
.venv/bin/program-vote-qr \
  --template program-back.pdf \
  --codes premiere-vote-codes.csv \
  --x 450 \
  --y 72 \
  --size 90 \
  --output premiere-program-backs.pdf
```

Coordinates and dimensions are PDF points, measured from the lower-left corner. `72` points is one inch. The default output includes the human-readable code below each QR. Use `--no-label` to omit it, or `--include-used` when deliberately regenerating already-used codes.

The output contains one copy of the selected template page per eligible CSV row. QR modules are drawn directly into the PDF as vector squares rather than raster images.

## Verification

```sh
.venv/bin/python -m pytest
```

Before printing, verify the output visually and scan at least the first, middle, and last pages. Keep the source CSV with the generated PDF so the printed batch remains traceable.

## License

MIT
