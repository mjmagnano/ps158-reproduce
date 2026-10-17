"""
Download the Federal Reserve Survey of Consumer Finances (SCF) "Summary Extract
Public Data" files for every triennial survey wave from 1989 through the latest
available wave.

Source / verified URLs (checked Oct 2026):
  - SCF program homepage:        https://www.federalreserve.gov/econres/scfindex.htm
  - Previous-surveys index:      https://www.federalreserve.gov/econres/scf-previous-surveys.htm
  - Per-wave summary extract CSV ("Summary Extract Public Data", CSV/Excel format):
        https://www.federalreserve.gov/econres/files/scfp{YEAR}excel.zip
    e.g. 1989: https://www.federalreserve.gov/econres/files/scfp1989excel.zip
         2022: https://www.federalreserve.gov/econres/files/scfp2022excel.zip
         2025: https://www.federalreserve.gov/econres/files/scfp2025excel.zip
    (SAS/Stata versions of the same files exist at scfp{YEAR}.zip / scfp{YEAR}s.zip;
    we use the CSV version because it needs no extra reader library.)

As of Oct 2026 the Federal Reserve released the 2025 SCF on Oct 9, 2026 (see
https://www.federalreserve.gov/econres/scf_2025.htm and the Oct 9, 2026 press
release), so the latest available wave is 2025, not 2022.

Each wave's summary extract contains one row per household per multiple-imputation
"implicate" (5 implicates per household), including (at minimum) the variables
EDCL (education of the household head/reference person: 1=no HS diploma,
2=HS diploma/GED, 3=some college, 4=college degree), NETWORTH, WGT (the
household weight, already scaled so that all 5 implicates together sum to the
number of US families -- no further division needed), and KIDS (number of the
household head's children living in the household).

DOLLAR BASIS: all dollar variables (including NETWORTH) in this public summary
extract are already expressed in REAL terms -- specifically, in the LATEST
survey wave's dollars (2025 dollars), using CPI-U-RS. This is how the Fed's own
publication macro (bulletin.macro.txt, linked from the SCF Chartbook) builds the
public release: every year 1989-2025 is deflated/inflated to a single common
CPI-U-RS base equal to the most recent wave's September value. Do not apply any
further inflation adjustment to these files. The Fed's pages for each survey say
"all dollar variables inflation-adjusted to 2025 dollars", and validate.py checks
that our numbers match the Fed's published tables in 2025 dollars.

This script is idempotent: it skips any wave whose CSV is already extracted in
data/, and only downloads/extracts what's missing.
"""

import io
import sys
import zipfile
from pathlib import Path

import requests

WAVES = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]

DATA_DIR = Path(__file__).resolve().parent / "data"
URL_TMPL = "https://www.federalreserve.gov/econres/files/scfp{year}excel.zip"


def wave_csv_path(year: int) -> Path:
    # The Fed names the CSV inside the zip SCFP{year}.csv (uppercase).
    return DATA_DIR / f"SCFP{year}.csv"


def download_wave(year: int) -> None:
    out_csv = wave_csv_path(year)
    if out_csv.exists():
        print(f"[{year}] already have {out_csv.name}, skipping")
        return

    url = URL_TMPL.format(year=year)
    print(f"[{year}] downloading {url}")
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Find the CSV member regardless of exact case used in the archive.
        csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not csv_members:
            raise RuntimeError(f"No CSV found in {url}; members={zf.namelist()}")
        member = csv_members[0]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with zf.open(member) as src, open(out_csv, "wb") as dst:
            dst.write(src.read())
    print(f"[{year}] extracted -> {out_csv}")


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for year in WAVES:
        try:
            download_wave(year)
        except Exception as exc:  # keep going so one failed wave doesn't kill the rest
            print(f"[{year}] FAILED: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
