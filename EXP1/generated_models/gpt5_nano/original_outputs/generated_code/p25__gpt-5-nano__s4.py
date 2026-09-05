import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    # Initialize model
    model = gp.Model()

    # Helpers and data extraction
    max_vehicles = len(data.get("vehicles", []))
    arcs = data["arcs"]  # list of [i, j]
    coords = {int(k): tuple(v) for k, v in data["coordinates"].items()}
    demand = {int(k): v for k, v in data["demand"].items()}
    time_window = {int(k): tuple(v) for k, v in data["time_window"].items()}
    service = {0: 0}
    for i in range(1, 21):
        service[i] = data["service_duration"][str(i)]
    big_m = data.get("big_m", 100000)

    # Precompute adjacency lists for arcs
    arcs_from = {}
    arcs_to = {}
    for (a, b) in arcs:
        arcs_from.setdefault(a, []).append(b)
        arcs_to.setdefault(b, []).append(a)

    # Distance function
    def distance(i, j):
        xi, yi = coords[i]
        xj, yj = coords[j]
        return math.hypot(xi - xj, yi - yj)

    # Create decision variables
    X = {}  # x_v_i_j for v in 1..max_vehicles, (i,j) in arcs
    variables = {}

    for (i, j) in arcs:
        for v in range(1, max_vehicles + 1):
            key = f"x_v{v}_{i}_{j}"
            var = model.addVar(vtype=GRB.BINARY, name=key)
            X[(v, i, j)] = var
            variables[key] = var

    # Time variables: t_v_i for v in 1..max_vehicles, i in 1..20
    T = {}
    for v in range(1, max_vehicles + 1):
        for i in range(1