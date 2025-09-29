
import math
def print_buses(grid):
    print("Buses:")
    print("| ID | Name    | Vnom (kV) |  V(pu)    |    V angle (degree)  | Load (MW)    | Generation (MW) |")
    print("|----|---------|-----------|-----------|----------------------|--------------|-----------------|")
    idx=0
    for bus in grid.get_buses():
        v_angle= bus.Va0 * 180 / math.pi
        idx=idx+1
        # Calculate total load in MW
        total_load = sum(load.P for load in bus.loads)
        # Calculate total generation in MW
        total_generation = sum(gen.P for gen in bus.controlled_generators)
        print(f"| {idx:2} | {bus.name:7} | {bus.Vnom:6}    | {bus.Vm0:7}   | {v_angle:20} | { total_load: 12} | {total_generation:15.6f} |")
        


# Function to print line details
def print_lines(grid):
    print("Branches:")
    print("| ID |        Name                         | Start Bus | End Bus | Thermal rate (MVA)| Impedance (pu) |")
    print("|----|-------------------------------------|-----------|---------|-------------------|----------------|")
    idx=0
    for line in grid.get_branches():
        idx=idx+1

        if idx ==13:
          print(f"| {idx:2} | {line.name:35} | {line.bus_from.name:9} | {line.bus_to.name:7} | {line.rate:18}| {line.r:11} ohm|")
        else:
          print(f"| {idx:2} | {line.name:35} | {line.bus_from.name:9} | {line.bus_to.name:7} | {line.rate:18}| {line.R:15}|")

def print_loads(grid):
    print("Loads:")
    print("| ID | Name    | P(MW)       |Q(MVAr)  | connected bus  |")
    print("|----|---------|-------------|---------|----------------|")
    idx=0
    for load in grid.get_loads():
        idx=idx+1
        print(f"| {idx:2} | {load.name:7} | {load.P:9} | {load.Q:7} | {load.bus.name:15}|")
def print_generators(grid):
    print("Generators:")
    print("| ID | Name    | P(MW)        |Pmax (MW)|Pmin(MW) |Qmax(MVAr)|Qmin (MVAr)|Vset(pu)|connected bus|")
    print("|----|---------|--------------|---------|---------|----------|-----------|--------|-------------|")
    idx=0
    for gen in grid.get_generators():
        idx=idx+1
        print(f"| {idx:2} | {gen.name:7} | {gen.P:12.6f} | {gen.Pmax:7} | {gen.Pmin:7} | {gen.Qmax:8} |{gen.Qmin:10} | {gen.Vset:6} | {gen.bus.name:12}|")
