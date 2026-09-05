import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for i, c_label in enumerate(centers, start=1):
        key = f"y_c{i}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f_vars = {}
    for i, c_label in enumerate(centers, start=1):
        for j, s_label in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            f_vars[key] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)

    # Objective: minimize opening costs + transportation costs
    opening_term = gp.quicksum(fixed_opening_cost[centers[i-1]] * y[f"y_c{i}"] for i in range(1, len(centers)+1))
    transport_term = gp.quicksum(
        transport_cost[centers[i-1]][stores[j-1]] * f_vars[f"f_c{i}_s{j}"]
        for i in range(1, len(centers)+1)
        for j in range(1, len(stores)+1)
    )
    model.modelSense = GRB.MINIMIZE
    model.setObjective(opening_term + transport_term)

    # Constraints
    # 1) Demand satisfaction: sum over centers equals demand for each store
    for j, s_label in enumerate(stores, start=1):
        model.addConstr(
            gp.quicksum(f_vars[f"f_c{i}_s{j}"] for i in range(1, len(centers)+1)) == demand[s_label]
        )

    # 2) Capacity constraints: sum over stores <= capacity * y_i
    for i, c_label in enumerate(centers, start=1):
        model.addConstr(
            gp.quicksum(f_vars[f"f_c{i}_s{j}"] for j in range(1, len(stores)+1)) <= capacity[c_label] * y[f"y_c{i}"]
        )

    # Pack variables into the required dict format
    variables = {}
    for i in range(1, len(centers)+1):
        variables[f"y_c{i}"] = y[f"y_c{i}"]
        for j in range(1, len(stores)+1):
            variables[f"f_c{i}_s{j}"] = f_vars[f"f_c{i}_s{j}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    objective = float(model.ObjVal)

    # Build solution dictionary in required order
    solution = {}
    for k in ["y_c1","y_c2","y_c3","y_c4","y_c5"]:
        solution[k] = float(variables[k].X)

    for i in range(1, 6):
        for j in range(1, 10):
            key = f"f_c{i}_s{j}"
            solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }