"""
Main command-line interface for the AC/DC dispatch workflow
==========================================================

This script stitches together the various building blocks provided in
the ``acdc_dispatch`` package to automate the construction of
Generation and HVDC Dispatch Scenarios (GHDS) from NYISO historical
data.  It is based on the workflow described in the accompanying
publication where five core modules are exposed as individual commands:

* ``nyiso_data_download`` – downloads and organizes the raw NYISO load
  and forecast CSV files for a particular month or day.  It accepts a
  target date and an output directory.
* ``data_processing`` – prepares the data for power‐flow analysis.
  Given a date, it loads the grid model, locates extreme operating
  points and scales the historical data accordingly.
* ``map_data_to_grid_model`` – maps the processed load and
  generation time‑series back onto the simplified two‑area power
  system model.
* ``run_power_flow`` – executes a time series power‑flow using
  GridCal on the prepared model.
* ``save_dispatch_scenarios`` – exports the time series results to
  a structured Excel workbook for further analysis.

There is also an ``add_grid_model`` command to load a custom
power‑flow model from a PSSE ``.raw`` file.  When no subcommand is
specified and a ``--date`` argument is provided, the script runs
through the entire workflow in sequence: downloading data, processing
it, mapping to the grid, solving the power flow and writing the
results to disk.  This design allows users to either inspect each
intermediate step separately or generate GHDS in a single command.

Note: this script provides a high‑level interface and defers the
numerical heavy lifting to functions in the ``acdc_dispatch`` package.
Any file paths used by those functions (e.g. default grid models) must
exist in your working environment.  If a required resource is
missing, the corresponding function will raise an exception which
propagates up to the caller.

"""

import argparse
import os
import pickle

from typing import Optional

"""
We intentionally avoid importing ``acdc_dispatch`` at module load time.  The
``acdc_dispatch`` package depends on third‑party libraries such as
GridCal which may not be installed in every environment.  By deferring
imports into the command handlers we allow the argument parser and
help system to function even when those dependencies are missing.  If
a user actually invokes one of the subcommands, we attempt to import
the required functions and propagate any ``ImportError`` exceptions up
to the caller, resulting in a clear runtime error message.
"""


def cmd_nyiso_data_download(args: argparse.Namespace) -> None:
    """Handle the ``nyiso_data_download`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed command‑line arguments with fields ``date`` and ``path``.
    """
    date = args.date
    dest = args.path or "_NYISO_Data"
    # Ensure destination directory exists before download
    os.makedirs(dest, exist_ok=True)
    # Lazy import: import only the nyiso_data_download module rather than
    # the package's top level.  This avoids triggering imports of
    # optional dependencies such as GridCal that may not be installed.
    import importlib
    try:
        mod = importlib.import_module('acdc_dispatch.nyiso_data_download')
        func = getattr(mod, 'nyiso_data_download')
    except ImportError as e:
        raise ImportError("The nyiso_data_download module requires missing dependencies. "
                          "Ensure that all prerequisites are installed.") from e
    func(date, dest, verbose=True)


def cmd_data_processing(args: argparse.Namespace):
    """Handle the ``data_processing`` subcommand.

    This wrapper invokes the :func:`acdc_dispatch.data_processing`
    function and persists the scaled data and grid object to disk when
    requested.  If ``--output`` is specified, the results are pickled
    for downstream consumption; otherwise they are discarded after
    printing a brief status message.
    """
    date = args.date
    # ``data_processing`` currently ignores the ``file_path`` argument
    # but it is left here for forward compatibility if a future
    # implementation consumes it.
    file_path = args.data_file or ""
    # Lazy import the data_processing module.  Note that this module
    # depends on GridCal; if that library is not installed the import
    # will raise ImportError and the caller will see the underlying
    # exception.  We propagate the error so users know they need to
    # install additional dependencies to perform this operation.
    import importlib
    mod = importlib.import_module('acdc_dispatch.data_processing')
    func = getattr(mod, 'data_processing')
    scaled, grid = func(date, file_path)
    if args.output:
        out_path = args.output
        with open(out_path, "wb") as f:
            # Persist both scaled dictionary and the grid model as a tuple
            pickle.dump((scaled, grid), f)
        print(f"✅ Data processing results saved to {out_path}")
    else:
        print("✅ Data processing complete – results not saved to disk")


def cmd_map_data_to_grid_model(args: argparse.Namespace):
    """Handle the ``map_data_to_grid_model`` subcommand.

    Reads a pickled tuple produced by ``data_processing`` (or another
    source) and returns a new grid with the time‑series profiles
    assigned.  The updated grid may optionally be saved as a pickled
    object to reuse in later stages.
    """
    input_file = args.data_file
    if not input_file:
        raise ValueError("--data_file is required for map_data_to_grid_model")
    with open(input_file, "rb") as f:
        scaled, grid = pickle.load(f)
    # Lazy import specific modules to avoid bringing in the entire
    # package.  Both modules rely on GridCal and will raise
    # ImportError if it is not available.
    import importlib
    map_mod = importlib.import_module('acdc_dispatch.map_data_to_grid_model')
    add_mod = importlib.import_module('acdc_dispatch.add_grid_model')
    map_data_func = getattr(map_mod, 'map_data_to_grid_model')
    add_grid_func = getattr(add_mod, 'add_grid_model')
    # When a custom model is supplied, load it; otherwise use the grid
    # returned from the data_processing stage.  Passing None allows
    # map_data_to_grid_model() to pick its own default internal model.
    if args.model:
        # Add the user‑supplied model to override the internal default
        grid = add_grid_func(args.model)
    mapped_grid = map_data_func(grid, scaled)
    if args.output:
        with open(args.output, "wb") as f:
            pickle.dump(mapped_grid, f)
        print(f"✅ Grid with profiles saved to {args.output}")
    else:
        print("✅ Mapping complete – grid not saved to disk")


def cmd_run_power_flow(args: argparse.Namespace):
    """Handle the ``run_power_flow`` subcommand.

    Loads a pickled grid (typically produced by ``map_data_to_grid_model``)
    and executes a time series power‑flow on it.  The resulting
    :class:`GridCal.Engine.Simulations.PowerFlow.time_series_driver.TimeSeriesResults`
    object is either saved as a pickle or simply reported as finished.
    """
    model_file = args.model
    if not model_file:
        raise ValueError("--model is required for run_power_flow")
    with open(model_file, "rb") as f:
        grid = pickle.load(f)
    # Lazy import: the run_power_flow module requires GridCal and
    # therefore may raise ImportError if that dependency is missing.
    import importlib
    mod = importlib.import_module('acdc_dispatch.run_power_flow')
    func = getattr(mod, 'run_power_flow')
    pf = func(grid)
    results = pf.results
    if args.output:
        with open(args.output, "wb") as f:
            pickle.dump(results, f)
        print(f"✅ Power flow results saved to {args.output}")
    else:
        print("✅ Power flow complete – results not saved to disk")


def cmd_save_dispatch_scenarios(args: argparse.Namespace):
    """Handle the ``save_dispatch_scenarios`` subcommand.

    Accepts a pickled ``TimeSeriesResults`` object and exports it to
    Excel using :func:`acdc_dispatch.save_dispatch_scenarios`.  The
    destination filename and output directory can be customised via
    ``--file_name`` and ``--path``.
    """
    pf_file = args.pf_results
    with open(pf_file, "rb") as f:
        pf_results = pickle.load(f)
    file_name = args.file_name or "gridcal_timeseries.xlsx"
    path = args.path or "."
    # Lazy import.  This module only depends on numpy/pandas and
    # should be safe to import even without GridCal.
    import importlib
    mod = importlib.import_module('acdc_dispatch.save_dispatch_scenarios')
    func = getattr(mod, 'save_dispatch_scenarios')
    func(pf_results, filename=file_name, path=path)


def cmd_add_grid_model(args: argparse.Namespace):
    """Handle the ``add_grid_model`` subcommand.

    Loads a PSSE ``.raw`` file into a GridCal grid.  The resulting grid
    is pickled to a specified output so that it can be passed to later
    stages of the pipeline.
    """
    file_path = args.file
    if not file_path:
        raise ValueError("--file is required for add_grid_model")
    # Lazy import.  The add_grid_model module requires GridCal.
    import importlib
    mod = importlib.import_module('acdc_dispatch.add_grid_model')
    func = getattr(mod, 'add_grid_model')
    grid = func(file_path)
    if args.output:
        with open(args.output, "wb") as f:
            pickle.dump(grid, f)
        print(f"✅ Grid model saved to {args.output}")
    else:
        print("✅ Grid model loaded – not saved to disk")


def run_full_pipeline(date: str, nyiso_path: str, output_dir: str) -> None:
    """Run the entire GHDS generation workflow for a given date.

    This helper function coordinates all individual stages: data
    download, processing, mapping, power flow and saving.  It writes
    intermediate artefacts into a temporary folder and emits the final
    Excel workbook into ``output_dir``.  The resulting file name
    encodes the input date as ``ghds_YYYY_MM_DD.xlsx``.

    Parameters
    ----------
    date : str
        Date string in ``MM-DD-YYYY`` format.
    nyiso_path : str
        Directory where NYISO data will be downloaded and organised.
    output_dir : str
        Directory where the final Excel workbook will be placed.
    """
    # Stage 1: download NYISO data
    os.makedirs(nyiso_path, exist_ok=True)
    import importlib

    # Stage 1: download NYISO data
    try:
        dl_mod = importlib.import_module('acdc_dispatch.nyiso_data_download')
        dl_func = getattr(dl_mod, 'nyiso_data_download')
    except ImportError as e:
        raise ImportError("Unable to import nyiso_data_download. Ensure dependencies are installed.") from e
    dl_func(date, nyiso_path, verbose=True)

    # Stage 2: process the downloaded data and build a scaled dispatch
    try:
        dp_mod = importlib.import_module('acdc_dispatch.data_processing')
        dp_func = getattr(dp_mod, 'data_processing')
    except ImportError as e:
        raise ImportError("Unable to import data_processing. Ensure GridCal and other dependencies are installed.") from e
    scaled, grid = dp_func(date, nyiso_path)

    # Stage 3: map the scaled data onto the grid and set up profiles
    try:
        map_mod = importlib.import_module('acdc_dispatch.map_data_to_grid_model')
        map_func = getattr(map_mod, 'map_data_to_grid_model')
    except ImportError as e:
        raise ImportError("Unable to import map_data_to_grid_model. Ensure GridCal is installed.") from e
    mapped_grid = map_func(grid, scaled)

    # Stage 4: run the time series power flow
    try:
        pf_mod = importlib.import_module('acdc_dispatch.run_power_flow')
        pf_func = getattr(pf_mod, 'run_power_flow')
    except ImportError as e:
        raise ImportError("Unable to import run_power_flow. Ensure GridCal is installed.") from e
    pf = pf_func(mapped_grid)

    # Stage 5: save the dispatch scenarios
    final_name = f"ghds_{date.replace('-', '_')}.xlsx"
    os.makedirs(output_dir, exist_ok=True)
    try:
        save_mod = importlib.import_module('acdc_dispatch.save_dispatch_scenarios')
        save_func = getattr(save_mod, 'save_dispatch_scenarios')
    except ImportError as e:
        raise ImportError("Unable to import save_dispatch_scenarios. Ensure pandas and numpy are installed.") from e
    save_func(pf.results, filename=final_name, path=output_dir)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top‑level argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate HVDC dispatch scenarios using NYISO historical data.\n"
            "Run individual stages with subcommands or specify --date to run the full pipeline."
        )
    )
    sub = parser.add_subparsers(dest="command")
    # nyiso_data_download
    p_dl = sub.add_parser(
        "nyiso_data_download",
        help="Download and organise NYISO load and forecast data for a given date"
    )
    p_dl.add_argument("--date", type=str, required=True, help="Date string (YYYY-MM or MM-DD-YYYY)")
    p_dl.add_argument("--path", type=str, default="_NYISO_Data", help="Destination folder for NYISO data")
    p_dl.set_defaults(func=cmd_nyiso_data_download)

    # data_processing
    p_dp = sub.add_parser(
        "data_processing",
        help="Process downloaded data and determine extreme operating conditions"
    )
    p_dp.add_argument("--date", type=str, required=True, help="Date string (MM-DD-YYYY)")
    p_dp.add_argument(
        "--data_file",
        type=str,
        help=(
            "Optional input file containing raw data.  Currently unused but reserved for future compatibility"
        ),
    )
    p_dp.add_argument(
        "--output",
        type=str,
        help="Write the scaled data and grid object to this pickle file",
    )
    p_dp.set_defaults(func=cmd_data_processing)

    # map_data_to_grid_model
    p_map = sub.add_parser(
        "map_data_to_grid_model",
        help="Map processed load and generation profiles onto a grid model"
    )
    p_map.add_argument("--data_file", type=str, required=True, help="Pickle file produced by data_processing")
    p_map.add_argument("--model", type=str, help="Optional PSSE .raw file to load as the base grid")
    p_map.add_argument("--output", type=str, help="Write the mapped grid to this pickle file")
    p_map.set_defaults(func=cmd_map_data_to_grid_model)

    # run_power_flow
    p_pf = sub.add_parser(
        "run_power_flow",
        help="Execute a time series power‑flow on a prepared grid"
    )
    p_pf.add_argument("--model", type=str, required=True, help="Pickle file containing the grid with profiles")
    p_pf.add_argument(
        "--output",
        type=str,
        help="Write the power flow results to this pickle file",
    )
    p_pf.set_defaults(func=cmd_run_power_flow)

    # save_dispatch_scenarios
    p_save = sub.add_parser(
        "save_dispatch_scenarios",
        help="Export TimeSeriesResults to an Excel workbook"
    )
    p_save.add_argument(
        "--pf_results",
        type=str,
        required=True,
        help="Pickle file containing the TimeSeriesResults from run_power_flow",
    )
    p_save.add_argument(
        "--file_name",
        type=str,
        default="gridcal_timeseries.xlsx",
        help="Name of the output Excel workbook",
    )
    p_save.add_argument(
        "--path",
        type=str,
        default=".",
        help="Directory to write the Excel file into",
    )
    p_save.set_defaults(func=cmd_save_dispatch_scenarios)

    # add_grid_model
    p_add = sub.add_parser(
        "add_grid_model",
        help="Load a PSSE .raw file into a GridCal grid and optionally persist it"
    )
    p_add.add_argument("--file", type=str, required=True, help="Path to the PSSE .raw file")
    p_add.add_argument("--output", type=str, help="Pickle file to save the loaded grid")
    p_add.set_defaults(func=cmd_add_grid_model)

    # Top‑level arguments for running the full pipeline
    parser.add_argument(
        "--date",
        type=str,
        help="Date string (MM-DD-YYYY) to run the full pipeline.  If provided without a subcommand, executes the entire workflow.",
    )
    parser.add_argument(
        "--nyiso_path",
        type=str,
        default="_NYISO_Data",
        help="Destination directory for downloaded NYISO data when running the full pipeline",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="dispatch_outputs",
        help="Directory where the final Excel file will be stored during the full pipeline run",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    # If a subcommand was provided, dispatch accordingly
    if hasattr(args, "func"):
        args.func(args)
        return
    # Otherwise, attempt to run the full pipeline if a date was specified
    if args.date:
        run_full_pipeline(args.date, args.nyiso_path, args.output_dir)
        return
    # No subcommand and no date: print help
    parser.print_help()


if __name__ == "__main__":
    main()