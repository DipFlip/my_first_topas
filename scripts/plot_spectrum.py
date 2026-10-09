#!/usr/bin/env python3
"""Validate native TOPAS AIDA XML and plot a detector pulse-height spectrum."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.special import ndtr

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution", type=float, default=0.03,
                        help="Fractional FWHM at 662 keV; default 0.03")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    out = args.results_dir.resolve()
    if args.resolution <= 0:
        parser.error("Resolution must be positive")
    inputs = (out / "input.txt").read_text()
    n = int(re.search(r"i:So/Gammas/NumberOfHistoriesInRun\s*=\s*(\d+)", inputs)[1])
    match = re.search(r"d:So/Gammas/BeamEnergy\s*=\s*([\d.]+)\s*(MeV|keV)", inputs)
    e_gamma = float(match[1]) * (1000 if match[2] == "MeV" else 1)
    log = (out / "topas.log").read_text()
    assert "TOPAS run sequence complete." in log, "TOPAS did not complete"
    logged_n = int(re.search(r"Particle source Gammas: Total number of histories: (\d+)", log)[1])
    assert logged_n == n, "Inputs changed since the saved run; rerun TOPAS"

    hist = ET.parse(out / "labr3.xml").find(".//histogram1d[@name='PulseHeight']")
    axis = hist.find("axis")
    bins = int(axis.get("numberOfBins"))
    edges = np.linspace(float(axis.get("min")), float(axis.get("max")), bins + 1) * 1000
    centers = (edges[:-1] + edges[1:]) / 2
    counts = np.zeros(bins)
    means = centers.copy()
    bin_entries = np.zeros(bins, dtype=int)
    for node in hist.findall("./data1d/bin1d"):
        index = node.get("binNum")
        assert index not in ("UNDERFLOW", "OVERFLOW"), "Increase histogram range"
        index = int(index)
        assert 0 <= index < bins, "Histogram contains underflow or overflow"
        counts[index] = float(node.get("height"))
        means[index] = float(node.get("weightedMean")) * 1000
        bin_entries[index] = int(node.get("entries"))
    recorded = int(hist.find("statistics").get("entries"))
    assert recorded == bin_entries.sum() == int(counts.sum()), "Histogram counts inconsistent"
    assert np.array_equal(counts, bin_entries), "Expected unbiased unit-weight events"

    total_mev, mean_mev, score_count = np.loadtxt(
        out / "energy_check.csv", delimiter=",")
    assert int(score_count) == recorded, "Independent scorer count disagrees"
    energy_from_hist = float(np.dot(counts, means) / 1000)
    # TOPAS CSV Sum is serialized as a float; allow its rounding precision.
    assert np.isclose(energy_from_hist, total_mev, rtol=1e-7), "Energy integral disagrees"
    assert np.isclose(energy_from_hist / n, mean_mev, rtol=1e-7)
    assert np.max(means[counts > 0]) <= e_gamma + 0.01, "Energy exceeds incident gamma"
    assert edges[-1] > e_gamma, "Gamma photopeak outside saved histogram"

    # Convolve the original 0.5 keV bins using their exact mean deposited energy.
    # FWHM(E) = R_662 * sqrt(662*E), all energies in keV.
    active = counts > 0
    mu = means[active]
    sigma = args.resolution * np.sqrt(662 * mu) / np.sqrt(8 * np.log(2))
    cdf = ndtr((edges[:, None] - mu[None, :]) / sigma[None, :])
    broadened = np.sum(np.diff(cdf, axis=0) * counts[active][None, :], axis=1)
    below = float(np.sum(cdf[0] * counts[active]))
    above = float(np.sum((1 - cdf[-1]) * counts[active]))
    assert np.isclose(broadened.sum() + below + above, recorded, atol=1e-6)

    peak_window = (means >= e_gamma - 0.5) & (means <= e_gamma + 0.01)
    peak_count = int(counts[peak_window].sum())
    edge = e_gamma * (1 - 1 / (1 + 2 * e_gamma / 510.99895))
    summary = {
        "engine": "OpenTOPAS 4.3.0 / Geant4 11.3.2",
        "image_digest": "sha256:e9e56294fac4e43ee77d0cc524a8411ce0637ffd8ca61992462dcfa2d774618e",
        "saved_input_sha256": hashlib.sha256(inputs.encode()).hexdigest(),
        "histories": n, "gamma_energy_keV": e_gamma,
        "geometry_and_physics": "See results/input.txt for the exact saved parameters",
        "events_with_energy_deposit": recorded,
        "events_with_no_energy_deposit": n - recorded,
        "fraction_with_energy_deposit": recorded / n,
        "near_full_energy_window_keV": [e_gamma - 0.5, e_gamma + 0.01],
        "near_full_energy_events": peak_count,
        "near_full_energy_fraction_per_launched_gamma": peak_count / n,
        "single_scatter_compton_edge_keV": edge,
        "assumed_resolution_fwhm_fraction_at_662_keV": args.resolution,
        "assumed_fwhm_at_photopeak_keV": args.resolution * np.sqrt(662 * e_gamma),
        "raw_histogram_energy_sum_MeV": energy_from_hist,
        "independent_energy_sum_MeV": float(total_mev),
        "relative_energy_sum_difference": abs(energy_from_hist - total_mev) / total_mev,
        "broadened_expected_counts_below_axis": below,
        "broadened_expected_counts_above_axis": above,
        "validation": "Event counts and independent energy integral agree",
    }
    np.savetxt(out / "spectrum.csv", np.column_stack(
        (edges[:-1], edges[1:], counts, means, broadened)), delimiter=",",
        header="bin_low_keV,bin_high_keV,raw_event_count,raw_bin_mean_keV,broadened_expected_count",
        comments="", fmt=["%.6f", "%.6f", "%d", "%.9f", "%.9f"])
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    group = 4
    assert bins % group == 0
    display_edges = edges[::group]
    raw_display = counts.reshape(-1, group).sum(axis=1)
    smooth_display = broadened.reshape(-1, group).sum(axis=1)
    channel_width = display_edges[1] - display_edges[0]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(11, 6.3), constrained_layout=True)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#ffffff")
    ax.stairs(raw_display, display_edges, color="#94a3b8", lw=1,
              label="TOPAS deposited energy per gamma")
    ax.stairs(smooth_display, display_edges, color="#087f8c", lw=2,
              label=f"With assumed {args.resolution:.0%} FWHM at 662 keV")
    ax.set_yscale("log")
    ax.set_ylim(1, max(raw_display.max(), smooth_display.max()) * 2.8)
    ax.set_xlim(0, edges[-1])
    ax.set_xlabel("Deposited / reconstructed energy (keV)")
    ax.set_ylabel(f"Counts per {channel_width:g} keV channel (log scale)")
    ax.set_title("LaBr₃ gamma-detector spectrum", loc="left", fontsize=20,
                 fontweight="bold", pad=35, color="#0f172a")
    diameter = 2 * float(re.search(r"d:Ge/Crystal/RMax\s*=\s*([\d.]+)\s*mm", inputs)[1])
    length = 2 * float(re.search(r"d:Ge/Crystal/HL\s*=\s*([\d.]+)\s*mm", inputs)[1])
    configuration = "housed crystal + rear scatterer" if "s:Ge/BackscatterBlock/Type" in inputs else ("housed crystal" if "s:Ge/Housing/Type" in inputs else "bare crystal")
    ax.text(0, 1.02, f"{n:,} monoenergetic {e_gamma:g} keV gammas  ·  {diameter:g} mm diameter × {length:g} mm {configuration}",
            transform=ax.transAxes, color="#475569", fontsize=11)
    ax.axvline(edge, color="#d97706", ls="--", lw=1, alpha=0.7)
    ax.annotate(f"Single-scatter Compton edge\n{edge:.1f} keV", xy=(edge, 350),
                xytext=(edge - 165, 1300), color="#9a5608",
                arrowprops={"arrowstyle": "->", "color": "#d97706"}, fontsize=10)
    ax.annotate(f"Full-energy photopeak\n{e_gamma:g} keV", xy=(e_gamma, smooth_display.max()),
                xytext=(e_gamma - 145, smooth_display.max() * 5), color="#076975",
                arrowprops={"arrowstyle": "->", "color": "#087f8c"}, fontsize=10)
    ax.text(0.24, 0.27, "Compton continuum", transform=ax.transAxes, color="#475569")
    ax.grid(axis="y", which="major", alpha=0.16)
    ax.legend(loc="upper left", frameon=False, fontsize=10)
    footer = (f"{recorded:,} events deposit energy ({recorded/n:.1%}); {n-recorded:,} deposit none.  "
              f"Resolution is assumed; no optical transport or intrinsic background.")
    fig.supxlabel(footer, fontsize=9, color="#475569")
    fig.savefig(out / "spectrum.png", dpi=180)
    fig.savefig(out / "spectrum.pdf")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
