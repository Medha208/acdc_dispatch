from GridCal.Engine import ReactivePowerControlMode
from GridCal.Engine.Simulations.PowerFlow import power_flow_worker as pfw
from GridCal.Engine.Simulations.PowerFlow.power_flow_driver import PowerFlowDriver

def power_flow(grid):
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
    # Define solver options
    options = pfw.PowerFlowOptions(
        pfw.bs.SolverType.NR,                      # Newton-Raphson solver
        verbose=True,                              # Print solver messages
        initialize_with_existing_solution=True,    # Use existing solution as initial point
        multi_core=False,                          # Single-core run
        tolerance=1e-9,                            # Convergence tolerance
        max_iter=99,                               # Maximum iterations
        control_q=ReactivePowerControlMode.Direct  # Reactive power control mode
    )
    # Create and run power flow
    pf = PowerFlowDriver(grid, options)
    pf.run()

    return pf
