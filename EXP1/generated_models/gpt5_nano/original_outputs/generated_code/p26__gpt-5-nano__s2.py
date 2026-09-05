from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    days = data["days"]
    students = data["students"]
    open_hours = data["open_hours_per_day"]
    max_shifts_per_week = data["max_shifts_per_week"]
    max_students_per_day = data["max_students_per_day"]
    min_undergrad = data["minimum_weekly_hours_undergrad"]
    min_grad = data["minimum_weekly_hours_grad"]

    wage = {int(k): v for k, v in data["wage"].items()}

    availability = {}
    for i in students:
        availability[i] = {}
        for d in days:
            availability[i][d] = int(data["availability_hours"][str(i)][d])

    model = Model()
    model.setParam('OutputFlag', 0)

    # Decision variables
    h = {}  # continuous hours
    y = {}  # binary shift indicator
    for i in students:
        for d in days:
            h[(i, d)] = model.addVar(lb=0.0, ub=availability[i][d], vtype=GRB.CONTINUOUS,
                                   name=f"h_{i}_{d}")
            y[(i, d)] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{d}")

    model.update()

    # Constraints
    # 1) Open hours constraint per day
    for d in days:
        model.addConstr(quicksum(h[(i, d)] for i in students) == open_hours,
                        name=f"OpenHours_{d}")

        # 2) Max number of students per day
        model.addConstr(quicksum(y[(i, d)] for i in students) <= max_students_per_day,
                        name=f"MaxStudents_{d}")

        # 3) Link hours to whether a student is scheduled that day
        for i in students:
            model.addConstr(h[(i, d)] <= availability[i][d] * y[(i, d)],
                            name=f"HoursLink_{i}_{d}")

    # 4) Weekly hours minimums and max shifts per week
    for i in students:
        total_hours = quicksum(h[(i, d)] for d in days)
        if i <= 4:
            model.addConstr(total_hours >= min_undergrad, name=f"MinHoursUndergrad_{i}")
        else:
            model.addConstr(total_hours >= min_grad, name=f"MinHoursGrad_{i}")

        # Max shifts per week
        model.addConstr(quicksum(y[(i, d)] for d in days) <= max_shifts_per_week,
                        name=f"MaxShifts_{i}")

    # Objective: minimize gross pay
    objective = quicksum(wage[i] * h[(i, d)] for i in students for d in days)
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()

    # Flattened variables dictionary to return
    variables = {}
    for i in students:
        for d in days:
            variables[f"h_{i}_{d}"] = h[(i, d)]
            variables[f"y_{i}_{d}"] = y[(i, d)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    objective = float(model.ObjVal)

    days = data["days"]
    solution = {}

    # h variables in required order
    for i in range(1, 7):
        for d in days:
            solution[f"h_{i}_{d}"] = float(variables[f"h_{i}_{d}"].X)
    # y variables in required order
    for i in range(1, 7):
        for d in days:
            solution[f"y_{i}_{d}"] = float(variables[f"y_{i}_{d}"].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }