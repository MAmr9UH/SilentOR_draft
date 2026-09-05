import math
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    model = Model()
    days = data["days"]
    open_hours_per_day = data.get("open_hours_per_day", 14)

    students = data["students"]

    # Containers for variables
    h = {}  # continuous hours
    y = {}  # binary whether scheduled on that day

    # Create variables
    for i in students:
        for d in days:
            ub = data["availability_hours"].get(str(i), {}).get(d, 0)
            h_key = f"h_{i}_{d}"
            y_key = f"y_{i}_{d}"
            h_var = model.addVar(lb=0.0, ub=ub, vtype=GRB.CONTINUOUS, name=h_key)
            y_var = model.addVar(vtype=GRB.BINARY, name=y_key)
            h[(i, d)] = h_var
            y[(i, d)] = y_var

    # Build a dictionary mapping for external access (as required)
    variables = {}
    for i in students:
        for d in days:
            variables[f"h_{i}_{d}"] = h[(i, d)]
            variables[f"y_{i}_{d}"] = y[(i, d)]

    # Constraints

    # 1) For each day, total hours must cover open_hours_per_day
    for d in days:
        model.addConstr(quicksum(h[(i, d)] for i in students) == open_hours_per_day)

    # 2) If a student is not scheduled that day, they cannot work hours that day
    for i in students:
        for d in days:
            model.addConstr(h[(i, d)] <= open_hours_per_day * y[(i, d)])

    # 3) At most max_students_per_day can be scheduled each day
    max_per_day = data["max_students_per_day"]
    for d in days:
        model.addConstr(quicksum(y[(i, d)] for i in students) <= max_per_day)

    # 4) Each student can be scheduled for at most max_shifts_per_week days
    max_shifts_per_week = data["max_shifts_per_week"]
    for i in students:
        model.addConstr(quicksum(y[(i, d)] for d in days) <= max_shifts_per_week)

    # 5) Minimum weekly hours for undergraduates
    min_undergrad = data["minimum_weekly_hours_undergrad"]
    for i in data["undergraduates"]:
        model.addConstr(quicksum(h[(i, d)] for d in days) >= min_undergrad)

    # 6) Minimum weekly hours for graduates
    min_grad = data["minimum_weekly_hours_grad"]
    for i in data["graduates"]:
        model.addConstr(quicksum(h[(i, d)] for d in days) >= min_grad)

    # Objective: minimize total wages
    model.setObjective(quicksum(data["wage"][str(i)] * h[(i, d)]
                               for i in students for d in days), GRB.MINIMIZE)

    model.update()
    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping to string (per allowed statuses)
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal) if model.Status == GRB.OPTIMAL else float("nan")

    # Build solution dictionary with all h and y values
    solution = {}
    for i in data["students"]:
        for d in data["days"]:
            solution[f"h_{i}_{d}"] = float(variables[f"h_{i}_{d}"].X)
    for i in data["students"]:
        for d in data["days"]:
            solution[f"y_{i}_{d}"] = float(variables[f"y_{i}_{d}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }