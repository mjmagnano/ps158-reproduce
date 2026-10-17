"""
Median net worth of families with a child at home, by the education of the
family head, for every SCF wave 1989-2025.

    python plot.py              # median (the headline figure)
    python plot.py --stat mean  # same figure with the mean, saved with a _mean suffix

INPUT: data/SCFP{year}.csv, downloaded by get_data.py (the Fed's Summary
Extract Public Data). Each file has 5 rows per family, one per
multiple-imputation "implicate". Columns used:
  - EDCL: education of the family head (1=no HS diploma, 2=HS diploma/GED,
          3=some college, 4=bachelor's degree or more)
  - NETWORTH: family net worth
  - WGT: survey weight
  - KIDS: number of the head's children living in the household

FAMILIES: only families with a child at home (KIDS > 0).
GROUPS: "College degree" = EDCL 4; "High school or less" = EDCL 1 or 2.
        "Some college" (EDCL 3) is left out of both.

WEIGHTS: all 5 implicate rows are pooled and weighted by WGT. In the summary
extract WGT is already scaled so that the rows of all 5 implicates together
sum to the number of US families, so no further division is needed.

DOLLARS: the Fed publishes every wave's summary extract in the latest wave's
dollars (2025 dollars, CPI-U-RS). No further inflation adjustment is applied.
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
WAVES = [1989, 1992, 1995, 1998, 2001, 2004, 2007, 2010, 2013, 2016, 2019, 2022, 2025]

GROUPS = {"college": [4], "hs_or_less": [1, 2]}
COLORS = {"college": "#2a78d6", "hs_or_less": "#eb6834"}
LABELS = {"college": "College degree", "hs_or_less": "High school or less"}


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    cum = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cum, cum[-1] / 2)])


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


STATS = {"median": weighted_median, "mean": weighted_mean}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stat", choices=STATS, default="median")
    stat = parser.parse_args().stat
    suffix = "" if stat == "median" else f"_{stat}"

    rows = []
    for year in WAVES:
        path = DATA_DIR / f"SCFP{year}.csv"
        if not path.exists():
            print(f"[{year}] missing {path.name}, skipping (run get_data.py first)")
            continue
        df = pd.read_csv(path, usecols=["EDCL", "NETWORTH", "WGT", "KIDS"])
        df = df[df["KIDS"] > 0]

        row = {"year": year}
        for name, edcl in GROUPS.items():
            sub = df[df["EDCL"].isin(edcl)]
            row[f"{name}_{stat}"] = STATS[stat](sub["NETWORTH"].to_numpy(), sub["WGT"].to_numpy())
            row[f"{name}_n_families"] = len(sub) // 5  # unweighted sample size
        rows.append(row)

    out = pd.DataFrame(rows)
    out["gap_dollars"] = out[f"college_{stat}"] - out[f"hs_or_less_{stat}"]
    out["ratio"] = out[f"college_{stat}"] / out[f"hs_or_less_{stat}"]

    out_csv = HERE / f"scf_wealth_gap_by_education{suffix}.csv"
    out.to_csv(out_csv, index=False)
    print(out.round(2).to_string(index=False))
    print(f"\nWrote {out_csv.name}")

    # ---- Figure ----
    fig, ax = plt.subplots(figsize=(8, 5))
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color("#b8b7b0")
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors="#55554f", length=0)

    last = out.iloc[-1]
    for name in GROUPS:
        y = out[f"{name}_{stat}"] / 1000
        ax.plot(out["year"], y, color=COLORS[name], linewidth=2, marker="o",
                markersize=5, label=LABELS[name])
        ax.annotate(f"{LABELS[name]}\n${last[f'{name}_{stat}'] / 1000:,.0f}K",
                    xy=(last["year"], y.iloc[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9, color="#2b2b28")

    ax.set_xticks(out["year"])
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlim(out["year"].min() - 1, out["year"].max() + 9)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("${x:,.0f}K"))
    ax.legend(frameon=False, loc="upper left")

    ax.set_title(f"{stat.capitalize()} net worth of families with a child at home,\n"
                 "by education of the family head (2025 dollars)",
                 loc="left", fontsize=12, color="#2b2b28")
    fig.text(0.01, 0.01,
             f"In 2025 the college {stat} is {last['ratio']:.1f}x the high-school-or-less {stat}. "
             "Some college excluded.\n"
             "Source: Federal Reserve, Survey of Consumer Finances, Summary Extract Public Data, 1989-2025.",
             fontsize=8, color="#55554f")
    fig.tight_layout(rect=[0, 0.06, 1, 1])

    out_png = HERE / f"wealth_gap_by_education{suffix}.png"
    fig.savefig(out_png, dpi=150)
    print(f"Wrote {out_png.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
