import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("ShiftScheduling")

    # Decision variables: number of workers on each shift (integer, non-negative)
    s1 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=GRB.INTEGER, lb=0, name="s4")

    # Demand constraints for each time window
    demand = data["workers_required_by_window"]  # list of 8 numbers
    cover = data["shift_coverage"]  # dict: shift -> list of windows it covers

    for w in range(8):
        lhs = 0
        for k in range(1, 5):
            cov_windows = cover[str(k)]
            if w in cov_windows:
                if k == 1:
                    lhs += s1
                elif k == 2:
                    lhs += s2
                elif k == 3:
                    lhs += s3
                elif k == 4:
                    lhs += s4
        model.addConstr(lhs >= demand[w], name=f"window_{w}")

    # Objective: minimize total wage cost
    wage = data["shift_wage"]
    obj = wage["1"] * s1 + wage["2"] * s2 + wage["3"] * s3 + wage["4"] * s4
    model.setObjective(obj, GRB.MINIMIZE)

    variables = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    st = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(st, str(st))

    obj_val = model.ObjVal

    # Read solution values
    s1_val = variables["s1"].X
    s2_val = variables["s2"].X
    s3_val = variables["s3"].X
    s4_val = variables["s4"].X

    solution = {
        "s1": s1_val,
        "s2": s2_val,
        "s3": s3_val,
        "s4": s4_val
    }

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }