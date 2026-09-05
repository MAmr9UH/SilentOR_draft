import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parameters from data
    a1 = data["supply"]["1"]
    a2 = data["supply"]["2"]

    b1 = data["demand"]["1"]
    b2 = data["demand"]["2"]

    q1 = data["station_capacity"]["1"]
    q2 = data["station_capacity"]["2"]

    f1 = data["fixed_cost"]["1"]
    f2 = data["fixed_cost"]["2"]

    c11 = data["cost_source_station"]["1,1"]
    c12 = data["cost_source_station"]["1,2"]
    c21 = data["cost_source_station"]["2,1"]
    c22 = data["cost_source_station"]["2,2"]

    cp11 = data["cost_station_demand"]["1,1"]
    cp12 = data["cost_station_demand"]["1,2"]
    cp21 = data["cost_station_demand"]["2,1"]
    cp22 = data["cost_station_demand"]["2,2"]

    # Decision variables
    x_11 = model.addVar(lb=0.0, name="x_1_1")
    x_12 = model.addVar(lb=0.0, name="x_1_2")
    x_21 = model.addVar(lb=0.0, name="x_2_1")
    x_22 = model.addVar(lb=0.0, name="x_2_2")

    z_11 = model.addVar(lb=0.0, name="z_1_1")
    z_12 = model.addVar(lb=0.0, name="z_1_2")
    z_21 = model.addVar(lb=0.0, name="z_2_1")
    z_22 = model.addVar(lb=0.0, name="z_2_2")

    y_1 = model.addVar(vtype=GRB.BINARY, name="y_1")
    y_2 = model.addVar(vtype=GRB.BINARY, name="y_2")

    # Constraints
    # Supply constraints
    model.addConstr(x_11 + x_12 <= a1, name="supply_1")
    model.addConstr(x_21 + x_22 <= a2, name="supply_2")

    # Demand constraints
    model.addConstr(z_11 + z_21 == b1, name="demand_1")
    model.addConstr(z_12 + z_22 == b2, name="demand_2")

    # Flow conservation at marshaling stations
    model.addConstr(x_11 + x_21 == z_11 + z_12, name="flow_1")
    model.addConstr(x_12 + x_22 == z_21 + z_22, name="flow_2")

    # Capacity with fixed-cost linkage
    model.addConstr(x_11 + x_21 <= q1 * y_1, name="cap_1")
    model.addConstr(x_12 + x_22 <= q2 * y_2, name="cap_2")

    # Objective
    objective = (
        c11 * x_11 + c12 * x_12 + c21 * x_21 + c22 * x_22 +
        cp11 * z_11 + cp12 * z_12 + cp21 * z_21 + cp22 * z_22 +
        f1 * y_1 + f2 * y_2
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Return model and dictionary of variables in the required format
    variables = {
        "x_1_1": x_11,
        "x_1_2": x_12,
        "x_2_1": x_21,
        "x_2_2": x_22,
        "z_1_1": z_11,
        "z_1_2": z_12,
        "z_2_1": z_21,
        "z_2_2": z_22,
        "y_1": y_1,
        "y_2": y_2
    }

    # Do not optimize here
    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    # Objective value
    objective = float(model.ObjVal)

    # Read solution values
    solution = {
        "x_1_1": float(variables["x_1_1"].X),
        "x_1_2": float(variables["x_1_2"].X),
        "x_2_1": float(variables["x_2_1"].X),
        "x_2_2": float(variables["x_2_2"].X),
        "z_1_1": float(variables["z_1_1"].X),
        "z_1_2": float(variables["z_1_2"].X),
        "z_2_1": float(variables["z_2_1"].X),
        "z_2_2": float(variables["z_2_2"].X),
        "y_1": float(variables["y_1"].X),
        "y_2": float(variables["y_2"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }