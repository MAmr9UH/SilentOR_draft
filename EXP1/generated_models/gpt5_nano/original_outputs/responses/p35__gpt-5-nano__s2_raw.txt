import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Suppress output for cleaner execution
    try:
        model.setParam('OutputFlag', 0)
    except Exception:
        pass

    # Decision variables
    x_11 = model.addVar(lb=0, name="x_1_1")
    x_12 = model.addVar(lb=0, name="x_1_2")
    x_21 = model.addVar(lb=0, name="x_2_1")
    x_22 = model.addVar(lb=0, name="x_2_2")

    z_11 = model.addVar(lb=0, name="z_1_1")
    z_12 = model.addVar(lb=0, name="z_1_2")
    z_21 = model.addVar(lb=0, name="z_2_1")
    z_22 = model.addVar(lb=0, name="z_2_2")

    y_1 = model.addVar(vtype=gp.GRB.BINARY, name="y_1")
    y_2 = model.addVar(vtype=gp.GRB.BINARY, name="y_2")

    # Data parameters
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

    c11_d = data["cost_station_demand"]["1,1"]
    c12_d = data["cost_station_demand"]["1,2"]
    c21_d = data["cost_station_demand"]["2,1"]
    c22_d = data["cost_station_demand"]["2,2"]

    # Objective
    model.setObjective(
        c11 * x_11 + c12 * x_12 + c21 * x_21 + c22 * x_22 +
        c11_d * z_11 + c12_d * z_12 + c21_d * z_21 + c22_d * z_22 +
        f1 * y_1 + f2 * y_2,
        sense=gp.GRB.MINIMIZE
    )

    # Constraints
    # Supply constraints
    model.addConstr(x_11 + x_12 <= a1, name="Supply_1")
    model.addConstr(x_21 + x_22 <= a2, name="Supply_2")

    # Demand constraints
    model.addConstr(z_11 + z_21 == b1, name="Demand_1")
    model.addConstr(z_12 + z_22 == b2, name="Demand_2")

    # Flow conservation at marshaling stations
    model.addConstr(x_11 + x_21 == z_11 + z_21, name="Flow_k1")
    model.addConstr(x_12 + x_22 == z_12 + z_22, name="Flow_k2")

    # Capacity with binary indicators
    model.addConstr(x_11 + x_21 <= q1 * y_1, name="Cap_k1")
    model.addConstr(x_12 + x_22 <= q2 * y_2, name="Cap_k2")

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

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_val = model.ObjVal

    solution = {
        "x_1_1": variables["x_1_1"].X,
        "x_1_2": variables["x_1_2"].X,
        "x_2_1": variables["x_2_1"].X,
        "x_2_2": variables["x_2_2"].X,
        "z_1_1": variables["z_1_1"].X,
        "z_1_2": variables["z_1_2"].X,
        "z_2_1": variables["z_2_1"].X,
        "z_2_2": variables["z_2_2"].X,
        "y_1": variables["y_1"].X,
        "y_2": variables["y_2"].X
    }

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }