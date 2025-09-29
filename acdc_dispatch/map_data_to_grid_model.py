from typing import Sequence
from acdc_dispatch import *

from GridCal.Engine.IO.file_handler import FileOpen
from GridCal.Engine.Devices import *
from GridCal.Engine.Core.multi_circuit import MultiCircuit

def map_data_to_grid_model(
    grid,scaled):
    """
    
    """
    grid = grid
    grid = add_grid_model("TwoAreas/PSSE_Files/2areas_mod_psse_ori2.raw")
    #Make a 24h time axis
    time_index= scaled ['time']
    T = len(time_index)
    grid.format_profiles(range(T))
    # set P_prof/Q_prof for loads
    for ld in grid.get_loads():
        if ld.name == "7_1":  # load1
            P = np.asarray(scaled["load1"], float)
        # Q: either your explicit "load1_Q" or PF from base
            Q = np.asarray(scaled["load1_Q"], float) if "load1_Q" in scaled else (float(ld.Q)/max(float(ld.P),1e-12))*P
            ld.P_prof, ld.Q_prof = P, Q
        if ld.name == "9_1":  # load2
            P = np.asarray(scaled["load2"], float)
            Q = np.asarray(scaled["load2_Q"], float) if "load2_Q" in scaled else (float(ld.Q)/max(float(ld.P),1e-12))*P
            ld.P_prof, ld.Q_prof = P, Q

    # set P_prof for generators (let PF handle Q via PV control)
    for g in grid.get_generators():
        if g.name in ("1_1", "2_1","3_1","4_1"):
            key = {"1_1":"G1", "2_1":"G2","3_1":"G3","4_1":"G4"}[g.name]
            g.P_prof = np.asarray(scaled[key], float)

    arr=[1000,1000,230,230,230,230,1000,1000,1000,1000,1000,1000]
    default_val = 1000.0
    for i, br in enumerate(grid.get_branches()):
        val = float(arr[i]) if i < len(arr) else default_val
        br.rate_prof = np.full(T, val, dtype=float)
            
    #set standard HVDC line
    for hvdc in grid.get_hvdc():
        hvdc.r= 0.05219584386  # resistance in ohm
        hvdc.Pset=200  #fixed
        #hvdc.angle_droop= 100000
        hvdc.Vset_f= 1
        hvdc.Vset_t= 1
        hvdc.rate=600

        P0 = float(getattr(hvdc, "Pset", getattr(hvdc, "P", 0.0)))  # use Pset if present
        Pprof = np.full(T, P0, dtype=float)

    
        hvdc.Pset_prof = Pprof
        rate_val = 600
        hvdc.rate_prof = np.full(T, rate_val, dtype=float)

    return grid
    

    
    
    
  

    

