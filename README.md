# ACDC Dispatch — End-to-End Notebook Workflow

Tools to download NYISO interface data, process it, map it to a grid model, run time-series/power-flow, and export structured Excel results.

## Contents
- [Prereqs](#prereqs)
- [Quick start (TL;DR)](#quick-start-tldr)
- [Install](#install)
  - [Conda (recommended)](#conda-recommended)
  - [venv (pip-only)](#venv-pip-only)
- [Start Jupyter](#start-jupyter)
- [Notebook workflow](#notebook-workflow)
- [Export results to Excel](#export-results-to-excel)
- [Repo layout](#repo-layout)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Prereqs
- **Python 3.10 or 3.11**
- Git (if installing from source)
- (Optional) Power-flow stack:
  - **GridCal** (used by the examples)
  - External OPF solvers (GLPK / CBC / CLP / Ipopt) — only if you plan to run OPF

---

## Quick start (TL;DR)

```bash
# 1) Create and activate a clean env
conda create -n acdc python=3.11 -y
conda activate acdc

# 2) Install dependencies
pip install -U pip
pip install numpy pandas requests openpyxl xlsxwriter jupyterlab matplotlib
pip install gridcal  # (or your preferred power-flow engine)

# 3) Install this library (from the repo root)
pip install -e .

# 4) Launch JupyterLab
jupyter lab
```

Then in a new notebook, run:

```python
from acdc_dispatch import (
    nyiso_data_download,      # data fetch
    data_processing,          # clean/transform/select day
    map_data_to_grid_model,   # attach to grid model
    run_power_flow,           # simulate
    save_dispatch_scenarios,  # export Excel (time column = 1..T)
)

date = "2024-06-17"
out_dir = "_NYISO_Data"

# 1) Download and organize raw data (creates folders under out_dir)
nyiso_data_download(date, out_dir)

# 2) Process → scale → build grid
scaled, grid = data_processing(date, out_dir)

# 3) Map processed signals to the grid model
mapped_grid = map_data_to_grid_model(grid, scaled)

# 4) Run time-series / power-flow
res = run_power_flow(mapped_grid)

# 5) Save results to Excel (time column = 1..T)
save_dispatch_scenarios(res, "powerflow_results.xlsx", out_dir)
```

---

## Install

### Conda (recommended)

**Option A — one-file environment (copy/paste as `environment.yml`):**
```yaml
name: acdc
channels:
  - conda-forge
dependencies:
  - python=3.11
  - numpy
  - pandas
  - requests
  - jupyterlab
  - matplotlib
  - openpyxl
  - xlsxwriter
  - pip
  - pip:
      - gridcal
```

Then:
```bash
conda env create -f environment.yml
conda activate acdc
pip install -e .          # install this repo in editable mode
```

**Option B — manual steps:**
```bash
conda create -n acdc python=3.11 -y
conda activate acdc
pip install -U pip
pip install numpy pandas requests openpyxl xlsxwriter jupyterlab matplotlib
pip install gridcal
pip install -e .
```

### venv (pip-only)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -U pip
pip install numpy pandas requests openpyxl xlsxwriter jupyterlab matplotlib
pip install gridcal
pip install -e .
```

> If you plan to run OPF:  
> `conda install -c conda-forge glpk coincbc ipopt` (platform dependent)

---

## Start Jupyter

```bash
conda activate acdc         # or: source .venv/bin/activate
jupyter lab                 # or: jupyter notebook
```
Open `http://localhost:8888` (auto-opens in most cases).

---

## Notebook workflow

1) **Import modules**
```python
from acdc_dispatch import (
    nyiso_data_download,
    data_processing,
    map_data_to_grid_model,
    run_power_flow,
    save_dispatch_scenarios,
)
```

2) **Define scenario**
```python
date = "2024-06-17"     # target day
out_dir = "_NYISO_Data" # output root for downloads & artifacts
```

3) **Download NYISO data**  
Fetches P-32 (“Internal & External Interface Limits & Flows”) and load data; organizes into subfolders.
```python
nyiso_data_download(date, out_dir)
```

4) **Process/scale**  
Cleans the CSVs, aligns datetimes, selects your day, and returns processed series & grid metadata.
```python
scaled, grid = data_processing(date, out_dir)
```

5) **Map to grid model**  
Attaches processed signals (e.g., interface limits/flows, load profiles) to the GridCal network.
```python
mapped_grid = map_data_to_grid_model(grid, scaled)
```

6) **Run simulation**  
Executes time-series/power-flow and returns `TimeSeriesResults`.
```python
res = run_power_flow(mapped_grid)
```

---

## Export results to Excel

The exporter writes multiple sheets (Bus_Vmag, Bus_Vang, Bus_P, Bus_Q, Branch_Pf/Qf/Pt/Qt, Branch_Losses_P/Q, HVDC_Pf/Pt/Losses, Convergence, Names).  
The **time column is forced to 1…T** (integers) for every sheet.

```python
save_dispatch_scenarios(res, "powerflow_results.xlsx", out_dir)
```
The file will be at: `./_NYISO_Data/powerflow_results.xlsx`

---

## Repo layout

```
acdc_dispatch/
  __init__.py                  # exports the public API
  nyiso_data_download.py       # download & organize MIS CSVs/ZIPs
  data_processing.py           # clean/align/slice day; scaling
  map_data_to_grid_model.py    # attach profiles/limits to grid
  run_power_flow.py            # run time-series/PF with GridCal
  save_dispatch_scenarios.py   # Excel exporter (time=1..T)
notebooks/
  ACDC_Demo.ipynb              # example notebook (optional)
```

---

## Troubleshooting

**Lots of Numba / solver warnings on import**  
Harmless for PF/time-series. Install solvers only if you need OPF:
```bash
conda install -c conda-forge glpk coincbc ipopt
```

**`NameError: requests is not defined`**  
Add `import requests` in any module doing HTTP requests.

**`IndentationError: unindent does not match any outer indentation level`**  
Convert all tabs to spaces (4 spaces). Most editors have “Convert Indentation to Spaces”.

**`KeyError: 'YYYY-MM-DD'` when slicing daily data**  
Use a robust day slice:
```python
import pandas as pd
d = pd.to_datetime(date).normalize()
df_day = df[(df.index >= d) & (df.index < d + pd.Timedelta(days=1))]
```

**Excel writer engine missing**  
Install one of:
```bash
pip install openpyxl xlsxwriter
```

**Huge branch loading values**  
Set realistic **MVA** ratings (not p.u.). For time series:
```python
T = len(res.time)
for br in mapped_grid.get_branches():
    br.rate_prof = np.full(T, 560.0, dtype=float)  # example constant rating in MVA
```

---

## FAQ

**Q: Which interfaces are “internal”?**  
Examples: CENTRAL EAST (aka CENT EAST), UPNY-CONED, DYSINGER EAST, MOSES SOUTH, TOTAL EAST. They’re included in the same P-32 feed as external ties; you filter by `Interface Name`.

**Q: What time stamps are used by NYISO P-32?**  
`RTD End Time Stamp` = end of 5-minute RTD interval (EPT). In our exporter, we output **1..T** instead.

**Q: Units for branch ratings?**  
**MVA**. Loading is dimensionless and computed as max(|S|)/MVA_rating.
