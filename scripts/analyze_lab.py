#!/usr/bin/env python3
"""Compare the controlled experiments and render real exported TOPAS tracks."""
import json
from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
import numpy as np
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results"


def vrml_points(chunk):
    match = re.search(r"point\s*\[([^]]+)\]", chunk, re.S)
    return np.fromstring(match[1].replace(",", " "), sep=" ").reshape(-1, 3)


def load_vrml(path):
    solids, tracks = {}, []
    for chunk in path.read_text().split("#---------- ")[1:]:
        kind = chunk.splitlines()[0]
        if kind.startswith("SOLID:"):
            points = vrml_points(chunk)
            faces_text = re.search(r"coordIndex\s*\[([^]]+)\]", chunk, re.S)[1]
            idx = np.fromstring(faces_text.replace(",", " "), sep=" ", dtype=int)
            faces, current = [], []
            for i in idx:
                if i == -1:
                    faces.append(current)
                    current = []
                else:
                    current.append(int(i))
            solids[kind.split(": ", 1)[1].split(":")[0]] = (points, faces)
        elif kind.startswith("POLYLINE"):
            tracks.append(vrml_points(chunk))
    return solids, tracks


def plot_comparison():
    series, summary, rear = {}, {}, {}
    for name in ("control", "backscatter"):
        series[name] = np.loadtxt(OUT / name / "spectrum.csv", delimiter=",", skiprows=1)
        summary[name] = json.loads((OUT / name / "summary.json").read_text())
        p = np.loadtxt(OUT / name / "rear_gammas.phsp")
        assert p.shape[1] == 13
        assert np.all(p[:, 7] == 22), "Phase space includes non-gammas"
        # Z+ face is behind the crystal, so negative local Z momentum is entry.
        returning = p[p[:, 8] == 1]
        rear[name] = {
            "rear_entry_gamma_crossings": len(returning),
            "distinct_histories_with_rear_entry": len(np.unique(returning[:, 10])),
            "rear_entry_crossings_under_300_keV": int((returning[:, 5] < 0.3).sum()),
            "note": "Crossings, not unique deposited-energy events; a gamma can recross",
        }
    assert summary["control"]["histories"] == summary["backscatter"]["histories"]
    # Ensure the control and experiment differ only by the block and output paths.
    def normalize(name):
        text = (OUT / name / "input.txt").read_text()
        text = re.sub(r"(?m)^[^#\n]*Ge/BackscatterBlock/.*\n", "", text)
        return "\n".join(l for l in text.replace("results/" + name, "RESULTS").splitlines()
                         if l.strip() and not l.lstrip().startswith("#"))
    assert normalize("control") == normalize("backscatter"), "Unmatched control"
    electron_mass = 510.99895
    e = summary["backscatter"]["gamma_energy_keV"]
    exact_backscatter = e / (1 + 2 * e / electron_mass)
    raw = series["backscatter"]
    grouped = raw[:, 4].reshape(-1, 10).sum(axis=1)
    lo = raw[::10, 0]
    peak_region = (lo >= 175) & (lo < 215)
    bump = float(lo[peak_region][np.argmax(grouped[peak_region])] + 2.5)
    delta = series["backscatter"][:, 4] - series["control"][:, 4]
    window = (raw[:, 0] >= 175) & (raw[:, 1] <= 215)
    diagnostics = {
        "histories_per_configuration": summary["control"]["histories"],
        "identical_source": "662 keV; uniform radius-60-mm disk at z=-100 mm; parallel +Z",
        "control_is_matched": True,
        "exact_180_degree_single_compton_energy_keV": exact_backscatter,
        "broadened_pulse_height_bump_center_5keV_channel": bump,
        "additional_expected_counts_175_to_215_keV": float(delta[window].sum()),
        "phase_space": rear,
        "pulse_height_validation": {k: v["validation"] for k, v in summary.items()},
        "resolution": "Assumed Gaussian 3% FWHM at 662 keV, absolute width scales as sqrt(E)",
    }
    (OUT / "lab_summary.json").write_text(json.dumps(diagnostics, indent=2) + "\n")

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12.8, 5.6), constrained_layout=True,
                            gridspec_kw={"width_ratios": [1.25, 1]})
    fig.patch.set_facecolor("#f8fafc")
    colors = {"control": "#64748b", "backscatter": "#087f8c"}
    labels = {"control": "Housing + reflector", "backscatter": "Housing + reflector + rear Al block"}
    for ax in axes:
        for name, data in series.items():
            edges = np.r_[data[::10, 0], data[-1, 1]]
            values = data[:, 4].reshape(-1, 10).sum(axis=1)
            ax.stairs(values, edges, color=colors[name], lw=2, label=labels[name])
        ax.set_xlabel("Reconstructed energy (keV)")
        ax.grid(axis="y", alpha=0.15)
        ax.set_ylabel("Expected counts per 5 keV channel")
    axes[0].set_yscale("log")
    axes[0].set_xlim(0, 800)
    axes[0].set_ylim(1, 50000)
    axes[0].set_title("Whole spectrum", loc="left", fontweight="bold")
    axes[0].legend(loc="upper left", frameon=False, fontsize=9)
    axes[0].annotate("662 keV\nphotopeak", xy=(662, 16000), xytext=(540, 26000),
                     arrowprops={"arrowstyle": "->", "color": "#087f8c"}, fontsize=10)
    axes[0].axvline(477.65, color="#d97706", lw=1, ls="--", alpha=0.7)
    axes[0].text(375, 440, "Compton edge", color="#9a5608", fontsize=9)
    axes[1].set_xlim(100, 290)
    axes[1].set_ylim(0, 1850)
    axes[1].set_title("Backscatter peak appears near 190 keV", loc="left", fontweight="bold")
    axes[1].axvline(exact_backscatter, color="#d97706", ls="--", lw=1.2)
    axes[1].annotate("180° single scatter\n184.35 keV", xy=(exact_backscatter, 1120),
                     xytext=(110, 1480), arrowprops={"arrowstyle": "->", "color": "#d97706"},
                     color="#9a5608", fontsize=10)
    fig.suptitle("LaBr₃ in a simple laboratory environment", fontsize=20, fontweight="bold",
                 color="#0f172a", x=0.01, ha="left")
    fig.supxlabel("Matched runs: 1,000,000 gammas each · Same broad beam · Assumed 3% FWHM at 662 keV",
                  fontsize=10, color="#475569")
    fig.savefig(OUT / "comparison.png", dpi=180)
    fig.savefig(OUT / "comparison.pdf")
    plt.close(fig)
    print(json.dumps(diagnostics, indent=2))


def plot_scene():
    solids, tracks = load_vrml(OUT / "scene/trajectories.wrl")
    assert set(solids) == {"Crystal", "Reflector", "Housing", "BackscatterBlock"}
    # Verify the exported actual geometry against the input dimensions.
    assert np.allclose(solids["BackscatterBlock"][0].min(axis=0), [-100, -100, 80])
    assert np.allclose(solids["BackscatterBlock"][0].max(axis=0), [100, 100, 120])
    assert np.allclose(solids["Crystal"][0][:, 2].min(), -25.4)
    assert np.allclose(solids["Crystal"][0][:, 2].max(), 25.4)

    returned, direct, transmitted = [], [], []
    for points in tracks:
        if not np.isclose(points[0, 2], -100):
            continue  # Secondary fluorescence tracks have different start locations.
        assert np.linalg.norm(points[0, :2]) <= 60.001
        assert np.allclose(points[1, :2], points[0, :2], atol=0.002), "Beam is not parallel +Z"
        in_block = np.where((points[:, 2] >= 80) & (points[:, 2] <= 120))[0]
        rear_crystal = np.where(np.isclose(points[:, 2], 25.4, atol=0.002)
                                & (np.linalg.norm(points[:, :2], axis=1) < 25.4))[0]
        if np.linalg.norm(points[0, :2]) > 27.4 and len(in_block) and len(rear_crystal):
            if in_block[0] < rear_crystal[-1] and points[rear_crystal[-1]-1, 2] > 25.4:
                returned.append(points)
        elif (np.linalg.norm(points[0, :2]) < 20 and points[:, 2].max() < 30
              and abs(points[-1, 2]) < 25.4 and np.linalg.norm(points[-1, :2]) < 25.4):
            direct.append(points)
        elif np.linalg.norm(points[0, :2]) > 30 and len(in_block):
            transmitted.append(points)
    assert returned, "No genuine block-to-crystal return track found"
    assert direct, "No direct crystal track found"
    absorbed_return = [p for p in returned if abs(p[-1,2]) < 25.4 and np.linalg.norm(p[-1,:2]) < 25.4]
    selected = {"Direct gamma → crystal": direct[:4],
                "Gamma → Al block → crystal": absorbed_return[:3],
                "Gammas illuminating the block": transmitted[:3]}
    palettes = {"Direct gamma → crystal": "#d97706",
                "Gamma → Al block → crystal": "#a21caf",
                "Gammas illuminating the block": "#94a3b8"}

    # Side projection of native tracks with exact nested material cross sections.
    fig, ax = plt.subplots(figsize=(9, 7.7), constrained_layout=True)
    fig.patch.set_facecolor("#f8fafc")
    ax.add_patch(Rectangle((80, -100), 40, 200, facecolor="#d9edf0", edgecolor="#087f8c", lw=1.4))
    for half, fill, edge_color in [(27.4, "#b8c2cc", "#475569"),
                                   (26.4, "#ffffff", "#9ca3af"),
                                   (25.4, "#f6db7f", "#b48b0a")]:
        ax.add_patch(Rectangle((-half, -half), 2*half, 2*half, facecolor=fill,
                              edgecolor=edge_color, lw=1, zorder=2))
    ax.plot([-100, -100], [-60, 60], color="#d97706", lw=4, alpha=0.55)
    for label in ("Gammas illuminating the block", "Direct gamma → crystal", "Gamma → Al block → crystal"):
        for i, p in enumerate(selected[label]):
            ax.plot(p[:, 2], p[:, 0], color=palettes[label], lw=1.5 if "→ Al" in label else 1,
                    alpha=0.85, zorder=4, label=label if i == 0 else None)
            # Direction arrow on the real first trajectory segment.
            a, b = p[0], p[1]
            start, end = a + 0.32*(b-a), a + 0.46*(b-a)
            ax.add_patch(FancyArrowPatch((start[2], start[0]), (end[2], end[0]),
                         arrowstyle="-|>", mutation_scale=12, color=palettes[label], zorder=5))
            if "→ Al" in label:
                # Pick the longest negative-Z segment before entry to the detector.
                candidates = np.diff(p, axis=0)
                j = np.argmin(candidates[:, 2])
                a, b = p[j], p[j+1]
                start, end = a + .3*(b-a), a + .5*(b-a)
                ax.add_patch(FancyArrowPatch((start[2], start[0]), (end[2], end[0]),
                             arrowstyle="-|>", mutation_scale=13, color=palettes[label], zorder=5))
    ax.text(-100, 76, "Gamma source plane\nz = −100 mm", ha="center", fontsize=11, color="#9a5608")
    ax.text(0, 73, "2-inch × 2-inch LaBr₃\n1 mm PTFE + 1 mm Al", ha="center", fontsize=11)
    ax.text(100, 107, "Aluminium scatterer\n200 × 200 × 40 mm", ha="center", fontsize=11, color="#076975")
    ax.text(0, 0, "LaBr₃", ha="center", va="center", fontweight="bold", color="#6b5300", zorder=7)
    ax.set_xlim(-120, 145)
    ax.set_ylim(-110, 130)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Beam axis z (mm) — incident gammas travel left to right (+z)")
    ax.set_ylabel("x (mm); y is projected out")
    ax.set_title("Simulated geometry and actual gamma paths", loc="left",
                 fontsize=18, fontweight="bold", pad=15, color="#0f172a")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    ax.grid(alpha=0.1)
    fig.supxlabel("Side projection; detector shown in central section.\nSelected real gamma tracks from a separate 2,000-event run.",
                  fontsize=10, color="#475569")
    fig.savefig(OUT / "scene.png", dpi=180)
    fig.savefig(OUT / "scene.pdf")
    plt.close(fig)

    # Interactive geometry is reconstructed from the exported native mesh, not guessed.
    fig3 = go.Figure()
    colors = {"Crystal": "#f6cb58", "Reflector": "#e7e9ed", "Housing": "#64748b", "BackscatterBlock": "#69b6c2"}
    names = {"Crystal": "LaBr₃ crystal", "Reflector": "1 mm PTFE reflector", "Housing": "1 mm aluminium housing",
             "BackscatterBlock": "Rear aluminium scatterer"}
    for name in ("BackscatterBlock", "Housing", "Reflector", "Crystal"):
        points, faces = solids[name]
        triangles = [(face[0], face[j], face[j+1]) for face in faces for j in range(1, len(face)-1)]
        i, j, k = np.array(triangles).T
        fig3.add_trace(go.Mesh3d(x=points[:, 0], y=points[:, 1], z=points[:, 2],
            i=i, j=j, k=k, color=colors[name], opacity=.16 if name != "Crystal" else .65,
            name=names[name], showlegend=True, hovertemplate=names[name] + "<extra></extra>"))
    theta = np.linspace(0, 2*np.pi, 121)
    fig3.add_trace(go.Scatter3d(x=60*np.cos(theta), y=60*np.sin(theta), z=np.full_like(theta, -100),
        mode="lines", line={"color": "#d97706", "width": 5}, name="Source disk: radius 60 mm, z = −100 mm"))
    for label, paths in selected.items():
        xyz = [p for points in paths for p in [*points.tolist(), [None, None, None]]]
        x, y, z = zip(*xyz)
        fig3.add_trace(go.Scatter3d(x=x, y=y, z=z, mode="lines",
            line={"color": palettes[label], "width": 5 if "→ Al" in label else 3},
            name=label, hovertemplate=label + "<br>x=%{x:.1f}, y=%{y:.1f}, z=%{z:.1f} mm<extra></extra>"))
    fig3.add_trace(go.Cone(x=[0], y=[0], z=[-65], u=[0], v=[0], w=[1],
        sizemode="absolute", sizeref=18, showscale=False, colorscale=[[0,"#d97706"],[1,"#d97706"]],
        name="Incident direction +z", hovertemplate="Incident direction +z<extra></extra>"))
    fig3.update_layout(title={"text": "LaBr₃ laboratory scene", "font": {"size": 19}},
        scene={"xaxis_title": "x (mm)", "yaxis_title": "y (mm)", "zaxis_title": "z (mm)",
               "xaxis": {"range": [-110,110]}, "yaxis": {"range": [-110,110]}, "zaxis": {"range": [-110,130]},
               "aspectmode": "data", "camera": {"eye": {"x":1.5,"y":1.2,"z":-.7}}},
        legend={"orientation":"h", "y":-.05}, margin={"l":0,"r":0,"t":60,"b":110}, height=730)
    fig3.write_html(OUT / "scene.html", include_plotlyjs=True, config={"responsive":True,"displaylogo":False})
    html = (OUT / "scene.html").read_text()
    html = html.replace("<head>", '<head><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="icon" href="data:,">')
    html = html.replace("<body>", '<body style="font-family:system-ui,sans-serif;margin:12px"><p>Drag to rotate; scroll to zoom. Click legend entries to hide the housing or other layers.</p>')
    html = html.replace("</body>", '<p>Native Geant4 material meshes and selected real gamma tracks. Source: uniform radius-60-mm disk at z = −100 mm; incident direction +z. The scene displays a sample of the tracks, not their relative rates.</p></body>')
    (OUT / "scene.html").write_text(html)
    data = {"native_vrml": "scene/trajectories.wrl", "native_gamma_polylines": len(tracks),
            "real_return_tracks_found": len(returned), "real_direct_absorption_tracks_found": len(direct),
            "displayed_tracks": {k: [p.tolist() for p in v] for k,v in selected.items()}}
    (OUT / "scene_tracks.json").write_text(json.dumps(data, indent=2) + "\n")
    print("Native mesh and track checks passed:", len(returned), "block-to-crystal tracks")


if __name__ == "__main__":
    plot_comparison()
    plot_scene()
