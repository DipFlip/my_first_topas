# LaBr3 gamma spectrum with OpenTOPAS

## Extended laboratory demo: backscatter and scene

Run the richer experiment with:

```bash
bash run_lab_demo.sh
```

The original bare-crystal demo remains available via `bash run_demo.sh`. Its
first completed outputs are also archived in `results/original/`.

The extended demo adds a **1 mm aluminium can** and a **1 mm PTFE reflector**
around the crystal, including end caps. It places a **200 × 200 × 40 mm aluminium
scatterer behind the detector**, spanning z=80 to 120 mm. The front of the can
is z=−27.4 mm, the rear is z=+27.4 mm, and the block is separated from the rear
by a 52.6 mm air gap. These are illustrative dimensions, not a specific
manufacturer's construction. PTFE is modeled as material for gamma/electron
transport; optical reflection and scintillation remain outside this model.

The source is a **parallel 662 keV gamma beam**, emitted uniformly over a
**60 mm radius disk at z=−100 mm**, traveling in **+z**. This deliberately
illuminates both the detector and the surrounding block. It is a source plane,
not an isotropic radioactive point source. The original 10 mm radius beam
was aimed entirely at the crystal; its fractions cannot be compared directly
with those of this wider beam.

The two new spectrum runs use **1,000,000 histories each**, identical source,
housing, reflector, physics and seed. The control omits only the rear block.
`results/comparison.png` and `.pdf` compare their spectra and zoom into the
backscatter region. With the block, a clear bump appears near **190 keV**.
For a 662 keV photon, exact 180° single Compton scattering gives **184.35 keV**;
the finite geometry admits other angles and multiple scattering, so its bump
is broader and shifted. The same assumed 3% detector resolution is applied to
both curves.

The rear-face phase-space diagnostic also records actual gamma energies,
positions, directions and history IDs. The checked run has **8,419 rear-entry
gamma crossings with the block, versus 626 without it**. Those counts represent
crossings, not pulse-height events; particles can cross more than once. The
analysis confirms matching controls and checks each pulse-height histogram
against its independent deposited-energy scorer.

### See the scene

* `results/scene.png` and `.pdf`: labeled side projection showing the source,
  materials and direction arrows on selected **real simulated gamma tracks**.
* `results/scene.html`: offline interactive 3D view; open it in a browser and drag
  to rotate. Click legend entries to hide the outer housing or other layers.
* `results/scene/geometry.wrl` and `trajectories.wrl`: native Geant4 exports.
* `results/scene_tracks.json`: the selected actual trajectories and validation
  counts. The tracks are selected for clarity, not sampled to represent rates.
* `results/lab_summary.json`: comparison and phase-space diagnostics.

The scene uses a separate **2,000-history** run of the same geometry. Its 3D
material meshes and trajectories are read from the native VRML export and
checked against the configured dimensions. Colour and transparency aid
inspection; they are display choices. The 2D view projects away y and shows the
detector's central material section, so some paths that miss in 3D can appear
to cross its outline in the projection.

The annotated input files are `lab_control.txt`, `lab_backscatter.txt`, and
`lab_scene.txt`. The runner uses these editable files directly. To regenerate
their default configuration, use `.venv/bin/python scripts/build_lab.py`.
The comparison checker deliberately rejects changes that make the control and
backscatter input differ beyond the rear block and output file paths.

Useful future improvements include a finite-distance isotope source, a full
Cs-137 decay spectrum, the actual detector housing/window/PMT geometry, and
LaBr3's intrinsic radioactive background. The current results demonstrate
transport and environmental backscatter; they are not a calibrated instrument
response.

## Original bare-crystal demo

This demo transports **200,000 individual 662 keV gamma rays** into a cylindrical
LaBr3 crystal, 50.8 mm in diameter and 50.8 mm long. It uses the official
OpenTOPAS v4.3.0 / Geant4 11.3.2 Docker image, pinned by digest, with native
Apple Silicon support. The beam is parallel to the cylinder axis and uniformly
illuminates a disk of radius 10 mm. All beam rays are aimed at the crystal;
reported fractions are per launched gamma in this geometry, not an isotropic
source's absolute detection efficiency.

## Run it

Docker Desktop must be running. From this directory:

```bash
bash run_demo.sh
```

The setup script downloads the three real CERN datasets used by this
electromagnetic-only example (about 330 MB compressed), verifies the official
Geant4 MD5 checksums, and caches them in `.cache/g4data`. It skips completed
downloads on later runs. Other TOPAS applications can require additional
datasets: this cache is intentionally specific to this example.

The simulation takes place inside Docker. Plotting uses a local Python virtual
environment with NumPy, SciPy and Matplotlib. The pinned plotting packages
support Python 3.9 and later. Existing output files are overwritten on rerun.

## What the spectrum means

TOPAS transports the gamma and its secondary particles using Geant4 Livermore
electromagnetic physics. The `EnergyDeposit` scorer sums energy deposited by
**all particles in the whole crystal per event**, then fills one histogram
entry. Do not filter this scorer to gamma tracks: much of the energy is
deposited by secondary electrons. Do not use `EBins` to obtain a pulse-height
spectrum: that bins a different quantity.

* The **photopeak near 662 keV** represents events that deposit essentially the
  entire gamma energy.
* The **Compton continuum** represents partial deposition followed by escape
  of scattered photons. The single-scatter Compton edge is about 478 keV;
  multiple scattering can deposit energy above this edge.
* Fluorescence escape can produce features below the full-energy peak.
* Gammas that deposit no energy have no histogram entry. The analysis reports
  those events separately, rather than adding them to the first energy bin.

The analysis also convolves the raw histogram with a Gaussian response with
**3% FWHM at 662 keV**, scaling its absolute width as sqrt(energy). This is an
illustrative response assumption, not a prediction of the actual detector's
resolution. It is applied to the binned TOPAS data and produces expected counts,
which may be fractional.

This is an ideal bare-crystal energy-deposition demo. It omits the small Ce dopant
fraction, hermetic housing, reflector, optical photon transport, photosensor,
electronics, light-yield nonlinearity, pileup, intrinsic La/Ac activity and room
background. The source is monoenergetic, not a full Cs-137 decay simulation.
There is no Ba-137 X-ray source component. No detector threshold is applied.

## Files and customization

* `labr3.txt`: annotated TOPAS inputs; edit `BeamEnergy`, `NumberOfHistoriesInRun`,
  crystal `RMax` and `HL`, or beam position to change the example. `HL` is **half
  the crystal length**, and `RMax` is its **radius**.
* `results/labr3*.xml`: original TOPAS pulse-height histogram.
* `results/energy_check.csv`: independent total-energy score for validation.
* `results/topas.log`: full TOPAS log, including engine versions and completion.
* `results/input.txt`: exact TOPAS inputs saved from the completed run.
* `results/spectrum.csv`: exported raw counts and broadened expected counts.
* `results/spectrum.png` and `results/spectrum.pdf`: spectrum figures.
* `results/summary.json`: counts, simulation metadata and consistency checks.

If increasing the gamma energy, also increase `HistogramMax` so the full-energy
peak remains inside the histogram. Keep `HistogramBins` large enough to resolve
the peak. The plotting script reads the source energy from the saved `results/input.txt`.
The histogram has 0.5 keV bins in this example; the figure groups them into
2 keV display channels.

## References

* [Official OpenTOPAS container documentation](https://opentopas.readthedocs.io/en/latest/getting-started/containers.html)
* [TOPAS histogram output](https://opentopas.readthedocs.io/en/latest/parameters/scoring/output.html#histogram-output)
* [TOPAS custom materials and mass fractions](https://opentopas.readthedocs.io/en/latest/parameters/material.html)
* [TOPAS native graphics and VRML export](https://opentopas.readthedocs.io/en/latest/parameters/graphics.html)
* [TOPAS phase-space scorer](https://opentopas.readthedocs.io/en/latest/parameters/scoring/phasespace.html)
* [Geant4 11.3.2 dataset definitions and checksums](https://gitlab.cern.ch/geant4/geant4/-/blob/v11.3.2/cmake/Modules/G4DatasetDefinitions.cmake)
* [Luxium detector resolution examples](https://www.luxiumsolutions.com/faqs):
  LaBr3 resolution depends on the crystal and sensor assembly; 3% is a demo assumption.
