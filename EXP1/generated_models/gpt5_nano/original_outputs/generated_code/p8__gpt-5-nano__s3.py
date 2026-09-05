import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    # Decision variables: number of workers assigned to each shift
    s1 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s4")

    # Objective: minimize total wage
    wages = data["shift_wage"]
    model.setObjective(
        wages["1"] * s1 + wages["2"] * s2 + wages["3"] * s3 + wages["4"] * s4,
        sense=GRB.MINIMIZE
    )

    # Coverage constraints for each 3-hour window (8 windows)
    required = data["workers_required_by_window"]
    coverage = data["shift_coverage"]

    for w in range(8):
        expr = 0
        if w in coverage.get("1", []):
            expr += s1
        if w in coverage.get("2", []):
            expr += s2
        if w in coverage.get("3", []):
            expr += s3
        if w in coverage.get("4", []):
            expr += s4
        model.addConstr(expr >= required[w], name=f"cover_w{w}")

    model.update()
    variables = {"s1": s1, "s2": s2, "s3": s3, "s4": s4}
    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    obj_val = model.ObjVal
    solution = {
        "s1": float(variables["s1"].X),
        "s2": float(variables["s2"].X),
        "s3": float(variables["s3"].X),
        "s4": float(variables["s4"].X)
    }

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }