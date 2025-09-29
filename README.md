# AC/DC Dispatch Workflow

This repository provides tools and scripts to generate **Generation and HVDC Dispatch Scenarios (GHDS)** using NYISO historical data.  
The environment is already prepared and exported into `environment.yml` for easy reproducibility.

---

## 1. Environment Setup

### With Conda
1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) 
2. Create the environment from the provided YAML file:
   ```bash
   conda env create -f environment.yml
   ```
  
3. Activate the environment:
   ```bash
   conda activate test
   ```



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
python main.py save_dispatch_scenarios --pf_results results.pkl --file_name powerflow_results.xlsx --path outputs
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

