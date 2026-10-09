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
  --placement 250,170,90 \
  --placement 646,170,90 \
  --output premiere-program-backs.pdf
```

Coordinates and dimensions are PDF points, measured from the lower-left corner. `72` points is one inch. Repeat `--placement X,Y,SIZE` for every QR slot on one template page. Codes are assigned left-to-right in placement order, then continue on the next output page. A final partially filled page keeps the unused template slots blank.

The default output prints both `Ballot NNN` and the five-character code below each QR. Use `--no-label` to omit both labels, `--include-used` when deliberately regenerating already-used codes, or `--start-ballot-number 1001` to change the first printed ballot number.

The output contains one copy of the selected template page per group of placements. QR modules are drawn directly into the PDF as vector squares rather than raster images.

## Two-up landscape program backs

The current San Diego program-back template is a landscape letter page (`792 x 612` points) with two backs side by side. A tested starting layout for that template is:

```sh
--placement 240,170,110 \
--placement 636,170,110
```

That places one 110-point QR in the blank area beside each `Audience Choice` block, with `Ballot NNN` and `Code: XXXXX` below it. At two ballots per sheet, 225 ballots produce 113 pages; the final page has one unused right-hand slot.

## Verification

```sh
.venv/bin/python -m pytest
```

Before printing, verify the output visually and scan at least the first, middle, and last pages. Keep the source CSV with the generated PDF so the printed batch remains traceable.

## License

MIT
