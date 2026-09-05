import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    days = data["days"]
    students = data["students"]
    open_hours_per_day = data["open_hours_per_day"]

    # Create decision variables
    h_vars = {}
    y_vars = {}

    for i in students:
        for d in days:
            avail = data["availability_hours"][str(i)][d]
            h = model.addVar(lb=0.0, ub=float(avail), vtype=GRB.CONTINUOUS, name=f"h_{i}_{d}")
            h_vars[(i, d)] = h
            y = model.addVar(lb=0.0, ub=1.0, vtype=GRB.BINARY, name=f"y_{i}_{d}")
            y_vars[(i, d)] = y

    model.update()

    # Objective: minimize total wages times hours
    wage = data["wage"]
    objective = gp.quicksum(float(wage[str(i)]) * h_vars[(i, d)] for i in students for d in days)
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraint: exactly open_hours_per_day hours must be covered each day
    for d in days:
        model.addConstr(gp.quicksum(h_vars[(i, d)] for i in students) == open_hours_per_day, name=f"cover_{d}")

    # Constraint: hours on a day cannot exceed 14 * y_i_d (i.e., if not scheduled, hours must be 0)
    for i in students:
        for d in days:
            model.addConstr(h_vars[(i, d)] <= 14.0 * y_vars[(i, d)], name=f"hours_if_scheduled_{i}_{d}")

    # Constraint: no more than 3 students can be scheduled on any day
    for d in days:
        model.addConstr(gp.quicksum(y_vars[(i, d)] for i in students) <= 3, name=f"max_students_per_day_{d}")

    # Weekly minimum hours per student
    for i in students:
        min_hours = 8 if i <= 4 else 7
        model.addConstr(gp.quicksum(h_vars[(i, d)] for d in days) >= min_hours, name=f"min_week_hours_{i}")

    # Maximum shifts per week per student
    max_shifts_per_week = data["max_shifts_per_week"]
    for i in students:
        model.addConstr(gp.quicksum(y_vars[(i, d)] for d in days) <= max_shifts_per_week, name=f"max_shifts_{i}")

    # Return the model and a dict of all variables with the required keys
    variables = {}
    for i in students:
        for d in days:
            variables[f"h_{i}_{d}"] = h_vars[(i, d)]
    for i in students:
        for d in days:
            variables[f"y_{i}_{d}"] = y_vars[(i, d)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_str = "UNKNOWN"
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE or status_code == GRB.INF_OR_UNBD:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    obj_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with all required keys
    solution = {}
    days = data["days"]
    students = data["students"]

    for i in students:
        for d in days:
            key = f"h_{i}_{d}"
            solution[key] = float(variables[key].X)

    for i in students:
        for d in days:
            key = f"y_{i}_{d}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": obj_value,
        "solution": solution
    }