import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi model for the given data.
    Returns (model, variables) where variables is a dict:
      keys are:
        "y_c1", "y_c2", "y_c3", "y_c4", "y_c5",
        "f_c1_s1", "f_c1_s2", ..., "f_c5_s5"
      values are the corresponding gurobipy Var objects (or dicts if nested).
    """
    centers = data["centers"]
    stores = data["stores"]

    m = gp.Model()

    # Decision variables
    variables = {}

    # Opening variables (binary)
    for c in centers:
        key = f"y_{c}"
        variables[key] = m.addVar(vtype=GRB.BINARY, name=key)

    # Flow variables (continuous, non-negative)
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    m.update()

    # Demands constraints: sum_c f_c_s == demand_s
    for s in stores:
        expr = gp.quicksum( variables[f"f_{c}_{s}"] for c in centers )
        m.addConstr(expr == data["demand"][s], name=f"dem_{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in centers:
        cap = data["capacity"][c]
        expr = gp.quicksum( variables[f"f_{c}_{s}"] for s in stores )
        m.addConstr(expr <= cap * variables[f"y_{c}"], name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum( data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers )
    transport_cost = gp.quicksum(
        data["transport_cost"][c][s] * variables[f"f_{c}_{s}"]
        for c in centers
        for s in stores
    )
    m.setObjective(opening_cost + transport_cost, GRB.MINIMIZE)

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string as per allowed set
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal)

    solution = {}
    # Read values for all variables
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }