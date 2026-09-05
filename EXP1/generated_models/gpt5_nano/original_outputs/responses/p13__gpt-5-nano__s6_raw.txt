import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()
    model.Params.OutputFlag = 0

    # Decision variables
    variables = {}

    # Opening decisions (binary)
    for c in centers:
        key = f"y_{c}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # Transportation decisions (continuous)
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            variables[key] = v

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj_transport = gp.quicksum(
        data["transport_cost"][c][s] * variables[f"f_{c}_{s}"] for c in centers for s in stores
    )
    obj_open = gp.quicksum(
        data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers
    )
    model.setObjective(obj_transport + obj_open, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction (equalities)
    for s in stores:
        demand = data["demand"][s]
        model.addConstr(gp.quicksum(variables[f"f_{c}_{s}"] for c in centers) == demand, name=f"demand_{s}")

    # Capacity constraints (only if center is opened)
    for c in centers:
        cap = data["capacity"][c]
        model.addConstr(gp.quicksum(variables[f"{c}_{s}"] for s in stores) <= cap * variables[f"y_{c}"], name=f"cap_{c}".replace("-", "_"))

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    from gurobipy import GRB

    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_value = float(model.ObjVal)

    # Extract solution values for all required variables
    solution_vals = {}
    for key, var in variables.items():
        solution_vals[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution_vals
    }