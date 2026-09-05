import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()

    days = data["days"]
    students = data["students"]

    wage = data["wage"]
    availability = data["availability_hours"]

    open_hours_per_day = data["open_hours_per_day"]

    undergrads = set(data["undergraduates"])
    grads = set(data["graduates"])

    # Decision variables
    h_vars = {}
    y_vars = {}

    for i in students:
        for d in days:
            key_h = f"h_{i}_{d}"
            key_y = f"y_{i}_{d}"
            max_hours = float(availability.get(str(i), {}).get(d, 0))
            h = model.addVar(lb=0.0, ub=max_hours, vtype=gp.GRB.CONTINUOUS, name=key_h)
            y = model.addVar(lb=0.0, ub=1.0, vtype=gp.GRB.BINARY, name=key_y)
            h_vars[key_h] = h
            y_vars[key_y] = y

    model.update()

    # Objective: minimize total wages
    objective = gp.quicksum(wage[str(i)] * h_vars[f"h_{i}_{d}"] for i in students for d in days)
    model.setObjective(objective, gp.GRB.MINIMIZE)

    # Constraints

    # 1) Daily coverage: sum of hours equals open_hours_per_day
    for d in days:
        model.addConstr(gp.quicksum(h_vars[f"h_{i}_{d}"] for i in students) == open_hours_per_day,
                        name=f"cover_{d}")

    # 2) Linking hours with binary shift indicator
    for i in students:
        for d in days:
            max_hours = float(availability.get(str(i), {}).get(d, 0))
            model.addConstr(h_vars[f"h_{i}_{d}"] <= max_hours * y_vars[f"y_{i}_{d}"])

            # Ensure if a student is scheduled (y=1) they contribute at least 1 hour
            model.addConstr(h_vars[f"h_{i}_{d}"] >= y_vars[f"y_{i}_{d}"])

    # 3) Weekly minimum hours per student
    for i in students:
        weekly_hours = gp.quicksum(h_vars[f"h_{i}_{d}"] for d in days)
        if i in undergrads:
            model.addConstr(weekly_hours >= data["minimum_weekly_hours_undergrad"])
        else:
            model.addConstr(weekly_hours >= data["minimum_weekly_hours_grad"])

    # 4) Maximum shifts per week per student
    max_shifts_per_week = data["max_shifts_per_week"]
    for i in students:
        weekly_shifts = gp.quicksum(y_vars[f"y_{i}_{d}"] for d in days)
        model.addConstr(weekly_shifts <= max_shifts_per_week)

    # 5) Maximum number of students on duty per day
    max_students_per_day = data["max_students_per_day"]
    for d in days:
        model.addConstr(gp.quicksum(y_vars[f"y_{i}_{d}"] for i in students) <= max_students_per_day)

    # Prepare flat variables dictionary with exact keys required
    variables = {}
    for i in students:
        for d in days:
            variables[f"h_{i}_{d}"] = h_vars[f"h_{i}_{d}"]
    for i in students:
        for d in days:
            variables[f"y_{i}_{d}"] = y_vars[f"y_{i}_{d}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_num = model.Status
    if status_num == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with required keys in the specified order
    solution = {}
    days = data["days"]
    for i in data["students"]:
        for d in days:
            key = f"h_{i}_{d}"
            solution[key] = float(variables[key].X)

    for i in data["students"]:
        for d in days:
            key = f"y_{i}_{d}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }