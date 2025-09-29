import os
import datetime
import zipfile
import urllib.request
import pandas as pd
import pickle
from tqdm import tqdm
from time import sleep
import os, io, zipfile
import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}  # some CDNs require a UA

# -------- helpers --------
def _parse_target_date(s: str):
    """
    Accepts one of: 'YYYY-MM', 'MM-YYYY', or 'MM-DD-YYYY'.
    Returns (year, month).
    """
    s = s.strip()
    fmts = ["%Y-%m", "%m-%Y", "%m-%d-%Y"]
    for fmt in fmts:
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return dt.year, dt.month
        except ValueError:
            pass
    raise ValueError("Date must be one of: 'YYYY-MM', 'MM-YYYY', or 'MM-DD-YYYY'.")

def _download_with_retries(url, file_path, retries=3, wait_sec=2):
    last_err = None
    for _ in range(retries):
        try:
            urllib.request.urlretrieve(url, file_path)
            return
        except Exception as e:
            last_err = e
            sleep(wait_sec)
    raise last_err

# -------- public API --------
def nyiso_data_download(target_date: str, destination_folder: str, verbose=True):
    year, month = _parse_target_date(target_date)

    now = datetime.datetime.now()
    if (year, month) > (now.year, now.month):
        raise ValueError("Cannot download data from the future.")

    load_forecast_path = os.path.join(destination_folder, "Load_Forecast", "00_Raw_Data", f"{year}")
    actual_load_path   = os.path.join(destination_folder, "Actual_Load",   "00_Raw_Data", f"{year}")
    os.makedirs(load_forecast_path, exist_ok=True)
    os.makedirs(actual_load_path,   exist_ok=True)

    # ----- 1) Download Load Forecast -----
    if not (year == 2001 and month < 6):
        filename = f"{year}{month:02d}01isolf_csv.zip"
        url      = f"http://mis.nyiso.com/public/csv/isolf/{filename}"
        zipfile_path = os.path.join(load_forecast_path, filename)

        for _ in tqdm(range(1), desc="Downloading Load Forecast", disable=not verbose):
            _download_with_retries(url, zipfile_path)
            with zipfile.ZipFile(zipfile_path, 'r') as zf:
                zf.extractall(zipfile_path[:-4])
            os.remove(zipfile_path)

    # ----- 2) Download Actual Load -----
    if not (year == 2001 and month < 6):
        filename = f"{year}{month:02d}01palIntegrated_csv.zip"
        url      = f"http://mis.nyiso.com/public/csv/palIntegrated/{filename}"
        zipfile_path = os.path.join(actual_load_path, filename)

        for _ in tqdm(range(1), desc="Downloading Actual Load", disable=not verbose):
            _download_with_retries(url, zipfile_path)
            with zipfile.ZipFile(zipfile_path, 'r') as zf:
                zf.extractall(zipfile_path[:-4])
            os.remove(zipfile_path)

    # ----- 3) Organize Forecast -----
    for _ in tqdm(range(1), desc="Organizing forecast data", disable=not verbose):
        organizing_forecast_data_per_zone(
            os.path.join(destination_folder, "Load_Forecast", "00_Raw_Data"),
            os.path.join(destination_folder, "Load_Forecast", "01_Processed_Data")
        )

    # ----- 4) Organize Actual -----
    for _ in tqdm(range(1), desc="Organizing actual load data", disable=not verbose):
        organizing_actual_load_data_per_zone(
            os.path.join(destination_folder, "Actual_Load", "00_Raw_Data"),
            os.path.join(destination_folder, "Actual_Load", "01_Processed_Data")
        )
     # ----- 5) Download interface daata-----
    fetch_p32_for_date(target_date, dest_dir="Interface_data", interface_name="CENTRAL EAST - VC")

def organizing_forecast_data_per_zone(raw_data_path, write_data_path):
    year_subfolders = os.listdir(raw_data_path)
    for year_subfolder in year_subfolders:
        year_subfolder_path = os.path.join(raw_data_path, year_subfolder)
        if not os.path.isdir(year_subfolder_path):  # skip stray files
            continue
        csv_subfolders = [os.path.join(year_subfolder_path, subf) for subf in os.listdir(year_subfolder_path)]
        for csv_subf in csv_subfolders:
            if not os.path.isdir(csv_subf):
                continue
            csv_files = [os.path.join(csv_subf, f) for f in os.listdir(csv_subf) if f.lower().endswith(".csv")]
            for csv_file in csv_files:
                df = pd.read_csv(csv_file)
                if "Time Stamp" not in df.columns:
                    continue
                zones = [c for c in df.columns if c != "Time Stamp"]
                ts = pd.to_datetime(df["Time Stamp"], format="%m/%d/%Y %H:%M", errors="coerce")
                for zone in zones:
                    df_zone = pd.DataFrame({
                        "Time Stamp": ts,
                        "Load Forecast": df[zone].ffill()
                    })
                    out_dir_csv = os.path.join(write_data_path, year_subfolder, zone.upper(), "csv")
                    out_dir_pkl = os.path.join(write_data_path, year_subfolder, zone.upper(), "pkl")
                    os.makedirs(out_dir_csv, exist_ok=True)
                    os.makedirs(out_dir_pkl, exist_ok=True)
                    base = os.path.basename(csv_file)
                    base_filename = base[:-9] + "_" + zone.upper() if len(base) > 9 else base + "_" + zone.upper()
                    df_zone.to_csv(os.path.join(out_dir_csv, base_filename + ".csv"), index=False)
                    with open(os.path.join(out_dir_pkl, base_filename + ".pkl"), "wb") as f:
                        pickle.dump(df_zone, f)

def organizing_actual_load_data_per_zone(raw_data_path, write_data_path):
    year_subfolders = os.listdir(raw_data_path)
    for year_subfolder in year_subfolders:
        year_subfolder_path = os.path.join(raw_data_path, year_subfolder)
        if not os.path.isdir(year_subfolder_path):
            continue
        csv_subfolders = [os.path.join(year_subfolder_path, subf) for subf in os.listdir(year_subfolder_path)]
        for csv_subf in csv_subfolders:
            if not os.path.isdir(csv_subf):
                continue
            csv_files = [os.path.join(csv_subf, f) for f in os.listdir(csv_subf) if f.lower().endswith(".csv")]
            for csv_file in csv_files:
                df = pd.read_csv(csv_file)
                if "Name" not in df.columns:
                    continue
                zones = df["Name"].dropna().unique()
                for zone in zones:
                    df_zone = df[df["Name"] == zone][["Time Stamp", "Integrated Load"]].copy()
                    df_zone["Time Stamp"] = pd.to_datetime(df_zone["Time Stamp"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
                    df_zone.rename(columns={"Integrated Load": "Load"}, inplace=True)
                    out_dir_csv = os.path.join(write_data_path, year_subfolder, str(zone), "csv")
                    out_dir_pkl = os.path.join(write_data_path, year_subfolder, str(zone), "pkl")
                    os.makedirs(out_dir_csv, exist_ok=True)
                    os.makedirs(out_dir_pkl, exist_ok=True)
                    base = os.path.basename(csv_file)
                    base_filename = base[:-17] + "_" + str(zone) if len(base) > 17 else base + "_" + str(zone)
                    df_zone.to_csv(os.path.join(out_dir_csv, base_filename + ".csv"), index=False)
                    with open(os.path.join(out_dir_pkl, base_filename + ".pkl"), "wb") as f:
                        pickle.dump(df_zone, f)




def fetch_p32_for_date(date, dest_dir="data", interface_name=None, timeout=45):
    """
    Download NYISO P-32 (Interface Limits & Flows) for a single day.
    - date_str: 'YYYY-MM-DD'
    - dest_dir: folder to save files
    - interface_name: if provided, writes a filtered CSV with only that interface
    Returns: (path_to_daily_csv, path_to_filtered_csv_or_None, df_full, df_filtered_or_None)
    """
    os.makedirs(dest_dir, exist_ok=True)  # <-- fixes your FileNotFoundError
    date_str = pd.to_datetime(date).strftime("%Y-%m-%d")

    day = pd.to_datetime(date).strftime("%Y%m%d")
    month_anchor =pd.to_datetime(date).strftime("%Y%m") + "01"

    daily_url = f"https://mis.nyiso.com/public/csv/ExternalLimitsFlows/{day}ExternalLimitsFlows.csv"
    daily_path = os.path.join(dest_dir, "LimitsFlows.csv")

    # 1) Try the daily CSV directly
    r = requests.get(daily_url, headers=HEADERS, timeout=timeout)
    if r.ok and r.content and r.status_code == 200 and len(r.content) > 0:
        with open(daily_path, "wb") as f:
            f.write(r.content)
        df = pd.read_csv(daily_path)
    else:
        # 2) Fallback: monthly ZIP, then extract the daily file
        zip_url = f"https://mis.nyiso.com/public/csv/ExternalLimitsFlows/{month_anchor}ExternalLimitsFlows_csv.zip"
        rz = requests.get(zip_url, headers=HEADERS, timeout=timeout)
        rz.raise_for_status()

        zf = zipfile.ZipFile(io.BytesIO(rz.content))
        member = f"{day}ExternalLimitsFlows.csv"
        if member not in zf.namelist():
            raise FileNotFoundError(
                f"{member} not found inside monthly archive: {zip_url}"
            )
        with zf.open(member) as zmem, open(daily_path, "wb") as out:
            out.write(zmem.read())
        df = pd.read_csv(daily_path)

    # Tidy types (optional but handy)
    time_col = "Timestamps" if "Timestamps" in df.columns else df.columns[0]
    df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
    for c in ("Flow (MWH)", "Positive Limit (MWH)", "Negative Limit (MWH)"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    filtered_path = None
    df_filt = None

    # 3) Optional: filter to a specific interface (e.g., "CENT EAST")
    if interface_name:
        name_col = "Interface Name"
        if name_col in df.columns:
            df_filt = df[df[name_col].astype(str).str.upper() == interface_name.upper()].copy()
            filtered_path = os.path.join(dest_dir, f"LimitsFlows_{interface_name.replace(' ','_')}.csv")
            df_filt.to_csv(filtered_path, index=False)

    # Always write the full-day CSV (already saved above), and return both
    return daily_path, filtered_path, df, df_filt





if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download NYISO load forecast and actual load data")
    parser.add_argument("--date", type=str, required=True,
                        help="Date: 'YYYY-MM', 'MM-YYYY', or 'MM-DD-YYYY' (e.g., 2023-08 or 08-2023 or 02-14-2024)")
    parser.add_argument("--path", type=str, default="./data", help="Directory to save data")
    parser.add_argument("--verbose", action="store_true", help="Show progress bars")
    args = parser.parse_args()
    nyiso_data_download(args.date, args.path, verbose=args.verbose)

