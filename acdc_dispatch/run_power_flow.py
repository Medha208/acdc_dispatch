import numpy as np
import pandas as pd

from GridCal.Engine import ReactivePowerControlMode
from GridCal.Engine.IO.file_handler import FileOpen

from GridCal.Engine.Devices import *
from GridCal.Engine.Core.multi_circuit import MultiCircuit

from GridCal.Engine.Simulations.PowerFlow.power_flow_worker import PowerFlowOptions, solve
from GridCal.Engine.Simulations.PowerFlow.power_flow_worker import *
from GridCal.Engine.Simulations.PowerFlow.time_Series_input import TimeSeriesInput
from GridCal.Engine.Simulations.PowerFlow.time_series_driver import TimeSeries
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import PowerFlowDriver
from GridCal.Engine.basic_structures import SolverType

def run_power_flow(grid):
    """
    Run a power flow simulation on the given grid.

    Parameters
    ----------
    grid : GridCal MultiCircuit or Grid object
        The grid model loaded into GridCal.

    Returns
    -------
    pf : PowerFlowDriver
        The power flow driver object containing results (pf.results).
    """
    #PF options & run TS-PF
   # --------------------------
    opts = PowerFlowOptions(bs.SolverType.NR,   
                           verbose = True,
                           initialize_with_existing_solution = True,
                           multi_core = False,
                           tolerance = 1e-9,
                          max_iter = 99,
                         control_q = ReactivePowerControlMode.Direct)
    pf = TimeSeries(grid, opts)
    pf.run()

    return pf
