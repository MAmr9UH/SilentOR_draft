import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    m = gp.Model()

    centers = data["centers"]
    stores = data["stores"]
    nC = len(centers)
    nS = len(stores)

    # Decision variables
    y_vars = {}
    for idx, c in enumerate(centers, start=1):
        key = f"y_c{idx}"
        y_vars[key] = m.addVar(vtype=GRB.BINARY, name=key)

    f_vars = {}
    for i, c in enumerate(centers, start=1):
        for j, s in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            f_vars[key] = m.addVar(lb=0.0, name=key)

    m.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.LinExpr()
    for idx, c in enumerate(centers, start=1):
        obj += opening_costs[c] * y_vars[f"y_c{idx}"]

    for i in range(1, nC + 1):
        c = centers[i - 1]
        for j in range(1, nS + 1):
            s = stores[j - 1]
            key = f"f_c{i}_s{j}"
            cost = transport_cost[c][s]
            obj += cost * f_vars[key]

    m.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    demand = data["demand"]
    capacity = data["capacity"]

    # Demand satisfaction: sum_i f_{i,j} = demand_j
    for j, s in enumerate(stores, start=1):
        m.addConstr(
            gp.quicksum(f_vars[f"f_c{i}_s{j}"] for i in range(1, nC + 1)) == demand[s],
            name=f"dem_{s}"
        )

    # Capacity: sum_j f_{i,j} <= capacity_i * y_i
    for i, c in enumerate(centers, start=1):
        cap = capacity[c]
        m.addConstr(
            gp.quicksum(f_vars[f"f_c{i}_s{j}"] for j in range(1, nS + 1)) <= cap * y_vars[f"y_c{i}"],
            name=f"cap_{c}"
        )

    m.update()

    # Prepare variables dict to return (exact keys)
    variables = {}
    for idx, c in enumerate(centers, start=1):
        variables[f"y_c{idx}"] = y_vars[f"y_c{idx}"]
    for i in range(1, nC + 1):
        for j in range(1, nS + 1):
            key = f"f_c{i}_s{j}"
            variables[key] = f_vars[key]

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    # Optional: silence output for clean runs
    try:
        model.setParam("OutputFlag", 0)
    except Exception:
        pass
    model.optimize()

    # Ensure variables are up-to-date for reading values
    model.update()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.CUTOFF: "CUTOFF"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    obj_val = float(model.ObjVal)

    solution = {}
    for key in sorted(variables.keys()):
        solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }