# AC/DC Dispatch Workflow

This repository provides tools and scripts to generate **Generation and HVDC Dispatch Scenarios (GHDS)** using NYISO historical data.  
The environment is already prepared and exported into `environment.yml` for easy reproducibility.

---

## 1. Environment Setup

### With Conda/Mamba
1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Mamba](https://mamba.readthedocs.io/).
2. Create the environment from the provided YAML file:
   ```bash
   conda env create -f environment.yml
   ```
   or
   ```bash
   mamba env create -f environment.yml
   ```
3. Activate the environment:
   ```bash
   conda activate acdc-ghds
   ```

### Notes
- The environment pins all required packages (including **GridCal**).
- If you do not want GUI dependencies, run headless by setting:
  ```bash
  export USE_GUI=0   # Linux/macOS
  set USE_GUI=0      # Windows PowerShell
  ```

---

## 2. Project Structure

```
project_root/
├── acdc_dispatch/        # library folder with modules
├── main.py               # CLI entry point
├── environment.yml       # exported environment file
└── README.md             # this file
```

---

## 3. Running the Script

### Option A: Run individual modules
```bash
python main.py nyiso_data_download --date 2024-06 --path _NYISO_Data
python main.py data_processing --date 06-18-2024 --output processed.pkl
python main.py map_data_to_grid_model --data_file processed.pkl --output grid.pkl
python main.py run_power_flow --model grid.pkl --output results.pkl
python main.py save_dispatch_scenarios --pf_results results.pkl --file_name ghds.xlsx --path outputs
```

### Option B: Run full pipeline
```bash
python main.py --date 06-18-2024
```

This will:
- Download NYISO data
- Process and map it to the grid
- Run a time-series power flow
- Export results to Excel under `dispatch_outputs/`

---

## 4. Verifying Setup
Quick import test:
```bash
python -c "from acdc_dispatch.nyiso_data_download import nyiso_data_download; print('OK')"
```

If you see `OK`, the package is accessible.

---

## 5. Troubleshooting

- **GridCal not found**: Ensure the environment was created with `environment.yml`.
- **Qt bindings missing**: Run `pip install PySide6`.
- **Headless mode**: Set `USE_GUI=0` as shown above.

---

✅ With `environment.yml` and this README, anyone can recreate the exact same setup and run the workflow.
