import gurobipy as gp

def build_model(data: dict):
    from gurobipy import GRB

    model = gp.Model("LabDutyScheduling")

    students = data["students"]
    days = data["days"]
    open_hours_per_day = data["open_hours_per_day"]

    # Wages and availability
    wage = {int(k): float(v) for k, v in data["wage"].items()}
    availability = {
        int(s): {d: float(data["availability_hours"][str(s)][d]) for d in days}
        for s in students
    }

    # Variables container
    variables = {"h_{}_{}".format(i, d): None for i in students for d in days}
    variables.update({"y_{}_{}".format(i, d): None for i in students for d in days})

    h = {}
    y = {}

    # Create variables
    for i in students:
        for d in days:
            ub = availability[i][d]
            hv = model.addVar(lb=0.0, ub=ub, vtype=gp.GRB.CONTINUOUS, name="h_{}_{}".format(i, d))
            yv = model.addVar(lb=0.0, ub=1.0, vtype=gp.GRB.BINARY, name="y_{}_{}".format(i, d))
            h[(i, d)] = hv
            y[(i, d)] = yv
            variables["h_{}_{}".format(i, d)] = hv
            variables["y_{}_{}".format(i, d)] = yv

    # Constraints

    # 1) Daily coverage: sum of hours equals open_hours_per_day
    for d in days:
        model.addConstr(gp.quicksum(h[(i, d)] for i in students) == open_hours_per_day,
                        name="DailyHours_{}".format(d))

    # 2) No more than 3 students scheduled per day
    for d in days:
        model.addConstr(gp.quicksum(y[(i, d)] for i in students) <= 3,
                        name="Max3PerDay_{}".format(d))

    # 3) Link hours and schedule: h <= 14 * y
    for i in students:
        for d in days:
            model.addConstr(h[(i, d)] <= 14 * y[(i, d)],
                            name="Link_hours_schedule_{}_{}".format(i, d))

    # 4) Weekly minimum hours per student
    min_undergrad = data["minimum_weekly_hours_undergrad"]
    min_grad = data["minimum_weekly_hours_grad"]

    undergrads = data["undergraduates"]
    grads = data["graduates"]

    for i in undergrads:
        model.addConstr(gp.quicksum(h[(i, d)] for d in days) >= min_undergrad,
                        name="MinWeeklyUndergrad_{}".format(i))
    for i in grads:
        model.addConstr(gp.quicksum(h[(i, d)] for d in days) >= min_grad,
                        name="MinWeeklyGrad_{}".format(i))

    # 5) Max shifts per week per student
    max_shifts_per_week = data["max_shifts_per_week"]
    for i in students:
        model.addConstr(gp.quicksum(y[(i, d)] for d in days) <= max_shifts_per_week,
                        name="MaxShiftsPerWeek_{}".format(i))

    # Objective: minimize gross pay
    objective = gp.quicksum(wage[i] * h[(i, d)] for i in students for d in days)
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Prepare status
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif status_code == gp.GRB.CUTOFF:
        status = "CUTOFF"
    else:
        status = str(status_code)

    model.update()
    objective = float(model.ObjVal)

    # Build solution dictionary in required order
    days = data["days"]
    solution = {}

    # h variables in order h_1_Mon, h_1_Tue, ..., h_6_Fri
    for i in data["students"]:
        for d in days:
            key = "h_{}_{}".format(i, d)
            solution[key] = float(variables[key].X)

    # y variables in order y_1_Mon, y_1_Tue, ..., y_6_Fri
    for i in data["students"]:
        for d in days:
            key = "y_{}_{}".format(i, d)
            solution[key] = float(variables[key].X)

    result = {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }
    return result