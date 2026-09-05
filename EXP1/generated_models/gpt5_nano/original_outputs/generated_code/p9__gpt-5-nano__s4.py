import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Extract data
    need = data.get("employees_needed", [0]*7)
    # Create model
    model = gp.Model()
    # Decision variables: s0..s6
    s = {}
    for i in range(7):
        s[i] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{i}")
    model.update()
    # Constraints: for each day j, sum of workers starting on days {j, j-1, ..., j-4} >= need[j]
    for j in range(7):
        indices = [(j - k) % 7 for k in range(5)]
        model.addConstr(gp.quicksum(s[i] for i in indices) >= need[j], name=f"cover_day_{j}")
    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(s[i] for i in range(7)), GRB.MINIMIZE)
    # Prepare variables dict with exact keys required
    variables = {f"s{i}": s[i] for i in range(7)}
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(st)
    # Objective value
    obj = float(model.ObjVal) if model.ObjVal is not None else None
    # Read solution
    model.update()
    solution = {f"s{i}": variables[f"s{i}"].X for i in range(7)}
    return {
        "status": status,
        "objective": obj,
        "solution": solution
    }