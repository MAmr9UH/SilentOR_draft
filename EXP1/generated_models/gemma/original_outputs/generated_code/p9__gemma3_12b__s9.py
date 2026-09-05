import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    days = data["days"]
    employees_needed = data["employees_needed"]
    work_days_consecutive = data["work_days_consecutive"]

    # Decision variables: number of workers starting each day
    s = {}
    for i in range(7):
        s[chr(ord('s') + i)] = model.addVar(vtype=GRB.INTEGER, name=f"s{i}")

    # Objective function: minimize the total number of employees
    model.setObjective(gp.quicksum(s[var] for var in s), GRB.MINIMIZE)

    # Constraints: meet daily employee requirements
    for i in range(7):
        day_index = i
        required = employees_needed[i]
        constraint_expr = gp.quicksum(
            s[chr(ord('s') + day_index)]
            if j == day_index
            else s[chr(ord('s') + (j + 5) % 7)]  # Shift for consecutive days
            for j in range(work_days_consecutive)
        )
        model.addConstr(constraint_expr >= required, f"demand_{days[i]}")

    variables = {
        "variables_keys": {
            "s0": "integer Var: workers starting on this day",
            "s1": "integer Var: workers starting on this day",
            "s2": "integer Var: workers starting on this day",
            "s3": "integer Var: workers starting on this day",
            "s4": "integer Var: workers starting on this day",
            "s5": "integer Var: workers starting on this day",
            "s6": "integer Var: workers starting on this day"
        },
        "note": "Keys s0..s6 (workers starting each day, 0=Monday)."
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "s0": float(s[chr(ord('s') + 0)].X),
        "s1": float(s[chr(ord('s') + 1)].X),
        "s2": float(s[chr(ord('s') + 2)].X),
        "s3": float(s[chr(ord('s') + 3)].X),
        "s4": float(s[chr(ord('s') + 4)].X),
        "s5": float(s[chr(ord('s') + 5)].X),
        "s6": float(s[chr(ord('s') + 6)].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }