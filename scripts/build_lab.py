#!/usr/bin/env python3
"""Create self-contained, matched TOPAS inputs for the laboratory demo."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "labr3.txt").read_text()


def replace(text, name, value):
    text, count = re.subn(r"(?m)^(?:[a-z]+):" + re.escape(name) + r"\s*=.*$",
                          lambda m: m[0].split("=")[0] + "= " + value, text)
    assert count == 1, name
    return text


housing = '''
# Nested cylinders form a 1 mm aluminium can and a 1 mm PTFE reflector,
# including front/rear end caps. Daughter volumes displace the parent material.
s:Ge/Housing/Type = "TsCylinder"
s:Ge/Housing/Parent = "World"
s:Ge/Housing/Material = "G4_Al"
d:Ge/Housing/RMax = 27.4 mm
d:Ge/Housing/HL = 27.4 mm
s:Ge/Housing/Color = "grey"
s:Ge/Housing/DrawingStyle = "WireFrame"
s:Ge/Reflector/Type = "TsCylinder"
s:Ge/Reflector/Parent = "Housing"
s:Ge/Reflector/Material = "G4_TEFLON"
d:Ge/Reflector/RMax = 26.4 mm
d:Ge/Reflector/HL = 26.4 mm
s:Ge/Reflector/Color = "white"
s:Ge/Reflector/DrawingStyle = "WireFrame"
'''

block = '''
# Deliberate rear scatterer: 200 x 200 x 40 mm aluminium block.
# Front face z=80 mm: 52.6 mm air gap from the can's rear face.
s:Ge/BackscatterBlock/Type = "TsBox"
s:Ge/BackscatterBlock/Parent = "World"
s:Ge/BackscatterBlock/Material = "G4_Al"
d:Ge/BackscatterBlock/HLX = 100 mm
d:Ge/BackscatterBlock/HLY = 100 mm
d:Ge/BackscatterBlock/HLZ = 20 mm
d:Ge/BackscatterBlock/TransZ = 100 mm
s:Ge/BackscatterBlock/Color = "lightblue"
s:Ge/BackscatterBlock/DrawingStyle = "WireFrame"
'''

diagnostic = '''
# Save real gamma crossings of the rear crystal face. Direction is in column 9.
# No killing or replay: this diagnostic scorer leaves transport unchanged.
s:Sc/RearGammas/Quantity = "PhaseSpace"
s:Sc/RearGammas/Surface = "Crystal/ZPlusSurface"
s:Sc/RearGammas/OutputType = "ASCII"
s:Sc/RearGammas/OutputFile = "RESULTS/rear_gammas"
s:Sc/RearGammas/IfOutputFileAlreadyExists = "Overwrite"
sv:Sc/RearGammas/OnlyIncludeParticlesNamed = 1 "gamma"
b:Sc/RearGammas/IncludeEventID = "True"
b:Sc/RearGammas/IncludeTrackID = "True"
b:Sc/RearGammas/IncludeParentID = "True"
'''

for scenario in ("lab_control", "lab_backscatter", "lab_scene"):
    out = "results/" + scenario.removeprefix("lab_")
    text = replace(base, "Ge/Crystal/Parent", '"Reflector"')
    text = replace(text, "So/Gammas/BeamPositionCutoffX", "60 mm")
    text = replace(text, "So/Gammas/BeamPositionCutoffY", "60 mm")
    histories = "2000" if scenario == "lab_scene" else "1000000"
    text = replace(text, "So/Gammas/NumberOfHistoriesInRun", histories)
    text = replace(text, "Sc/XmlFileName", f'"{out}/labr3"')
    text = replace(text, "Sc/EnergyCheck/OutputFile", f'"{out}/energy_check"')
    text = text.replace("uniformly over a 10 mm radius disk", "uniformly over a 60 mm radius disk")
    text = text.replace("# LaBr3 gamma spectroscopy demo.", "# Housed LaBr3 laboratory demo.")
    text += housing
    if scenario != "lab_control":
        text += block
    text += diagnostic.replace("RESULTS", out)
    if scenario == "lab_scene":
        text += '''
# Native Geant4 export with real trajectories from a separate small run.
s:Gr/Scene/Type = "VRML"
b:Gr/Scene/IncludeGeometry = "True"
b:Gr/Scene/IncludeTrajectories = "True"
b:Gr/Scene/UseSmoothTrajectories = "False"
s:Gr/Scene/ColorBy = "ParticleType"
sv:Gr/OnlyIncludeParticlesNamed = 1 "gamma"
s:Gr/RefreshEvery = "Run"
'''
    (ROOT / (scenario + ".txt")).write_text(text)
    (ROOT / out).mkdir(parents=True, exist_ok=True)
    print(scenario, histories, out)
