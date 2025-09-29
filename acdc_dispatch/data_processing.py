import os
import numpy as np

import pandas as pd

from GridCal.Engine.IO.file_handler import FileOpen
from acdc_dispatch import *
 

def find_extreme_points(grid):
    """
    Stub: Find extreme points in the grid.
    For now: -base case
      -highest loading
      -no transfer
     """

    #base case
    grid = add_grid_model("TwoAreas/PSSE_Files/2areas_mod_psse_ori.raw")
    # Power flow 
    pf = power_flow(grid)

    #initialize
    load_increment= 10 #MW
    for load in grid.get_loads():
        if load.name== '9_1':
            loadP= load.P
            loadQ= load.Q  
    for g in grid.get_generators():
        if g.name =='1_1':
            gen = g.P

    load_base= loadP

    #highest load case
    # Loop to increase Load and check convergence
    while True:
    # Increase the load by 10 MW
        loadP += load_increment
        loadQ += load_increment
        if gen < 9999:
            gen += load_increment
            
        for load in grid.get_loads():
            if load.name == '9_1':
                load.P = loadP
                load.Q = loadQ

        for g in grid.get_generators():
            if g.name == '1_1':
                g.P = gen
        pf = power_flow(grid)
    
    
        if not pf.results.converged:
            loadP -= load_increment
            loadQ -= load_increment
            gen -= load_increment
            break
        load_h=loadP

        #light loading(no transfer: got the condition by changing the values to check 0 transfer: ref:4_extremeCases.ipynb)
        load_no=1500


    return {"base": load_base, "high": load_h, "no_transfer": load_no}


# -------------------------------------------------------------------
# Scale down data
# -------------------------------------------------------------------
def scale_down(date, extremes):
    """
    Stub: Scale down numerical values in a dictionary by a factor.
    """
    _time_stamps, _load11, _best1, _worst1 = visualize_load_forecast(date, 'CENTRL', "_NYISO_Data", False)
    _time_stamps, _load12, _best1, _worst1 = visualize_load_forecast(date, 'WEST', "_NYISO_Data", False)
    _time_stamps, _load13, _best1, _worst1 = visualize_load_forecast(date, 'GENESE', "_NYISO_Data", False)

    _time_stamps, _load21, _best2, _worst2 = visualize_load_forecast(date, 'DUNWOD', "_NYISO_Data", False)
    _time_stamps, _load22, _best3, _worst3 = visualize_load_forecast(date, 'MILLWD', "_NYISO_Data", False)
    _time_stamps, _load23, _best4, _worst4 = visualize_load_forecast(date, "N.Y.C.", "_NYISO_Data", False)
    _time_stamps, _load24, _best4, _worst4 = visualize_load_forecast(date, "LONGIL", "_NYISO_Data", False)

    import numpy as np
    load1= np.array(_load11)+np.array(_load12)+np.array(_load13)
    load2= np.array(_load21)+np.array(_load22)+np.array(_load23)++np.array(_load24)

    # power flow between zones data 
    import pandas as pd
    # Load data once
    
 
    df = pd.read_csv("Interface_data/LimitsFlows_CENTRAL_EAST_-_VC.csv", parse_dates=["Timestamp"])
    df.set_index("Timestamp", inplace=True)

   # Filter by specific date
   
    specific_date = pd.to_datetime(date).strftime("%Y-%m-%d")
    df_day = df.loc[specific_date]

    

    # Resample to hourly means
    hourly_flow = df_day["Flow (MWH)"].resample("H").mean()
    hourly_limit = df_day["Positive Limit (MWH)"].resample("H").mean()
    # Create a new list that is the element-wise sum of _load1 and hourly_flow
    total_dispatch_zone1= [i + j for i, j in zip(load1, hourly_flow)]
    #divide by capacity ratio of two generator
    G1_cap= 1300
    G2_cap= 1000
    total= G1_cap+ G2_cap

    G1_dispatch = [x * G1_cap/ total for x in total_dispatch_zone1]
    G2_dispatch = [x * G2_cap/ total for x in total_dispatch_zone1]

    total_dispatch_zone2= [i - j for i, j in zip(load2, hourly_flow)]
    #divide by capacity ratio of two generator
    G3_cap= 6500.5
    G4_cap= 5549.5
    total= G3_cap+ G4_cap

    G3_dispatch = [x * G3_cap/ total for x in total_dispatch_zone2]
    G4_dispatch = [x * G4_cap/ total for x in total_dispatch_zone2]

    #for load 2
    #base case
    x1= np.mean(load2)
    y1= extremes['base']

    #heavy loading
    x2= np.max(load2)
    y2=extremes['high']

    #light loading
    x3=np.min(load2)
    y3= extremes["no_transfer"]
    import numpy as np


    points = [(x1, y1), (x2, y2), (x3, y3)]

    # Create matrices for the linear equation Ax = B
    A = [[points[0][0]**2, points[0][0], 1],
     [points[1][0]**2, points[1][0], 1],
     [points[2][0]**2, points[2][0], 1]]

    B = [points[0][1], points[1][1], points[2][1]]

    # Solve the linear equations using numpy's linear algebra solver
    coefficients = np.linalg.solve(A, B)
    a, b, c = coefficients
    x_values = list(range(0, 24))
    x=load2
    scaled_load2 = a * x ** 2 + b * x + c
    #for load 1
    base_load= 967
    max_value= np.max(load1)
    scaled_load1= [base_load * i / max_value for i in load1]


    scaling_factor1= [j/i for i,j in zip(load1, scaled_load1)]
    scaled_G1= [ i*j for i,j in zip(G1_dispatch, scaling_factor1)]
    scaling_factor2= [j/i for i,j in zip(load2, scaled_load2)]
    scaled_G3= [i*j for i,j in zip(G3_dispatch, scaling_factor2)]
    scaled_G4= [i*j for i,j in zip(G4_dispatch, scaling_factor2)]
    factor_tie= [(i*k+j*l)/(2*(k+l)) for i,j,k,l in zip(scaling_factor1,scaling_factor2,total_dispatch_zone1,total_dispatch_zone2)]
    p_tie_scaled= [m*n/2 for m,n in zip(hourly_limit, factor_tie)]

   

    scaled_G2=[i+j-k-l-m for i,j,k,l,m in zip(scaled_load1, scaled_load2,scaled_G1, scaled_G3,scaled_G4)]

    return {
        "load1":        scaled_load1,
        "load2":        scaled_load2,
        "G1":           scaled_G1,
        "G2":            scaled_G2,
        "G3":           scaled_G3,
        "G4":           scaled_G4,
        "time":        _time_stamps,
        "tie_rate":     p_tie_scaled

    }


# -------------------------------------------------------------------
# Main function: Data processing workflow
# -------------------------------------------------------------------
def data_processing(date: str, file_path: str):
    """
    Full data processing pipeline:
      1. Load grid model
      2. Find extreme points
      3. Scale down results
    """

    grid = add_grid_model("TwoAreas/PSSE_Files/2areas_mod_psse_ori.raw")
    extremes = find_extreme_points(grid)
    scaled = scale_down(date, extremes)

    print(f"Data Processed")

    return scaled, grid
