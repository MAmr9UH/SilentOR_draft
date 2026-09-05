import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Build the Gurobi model with all decision variables, constraints, and objective.
    model = gp.Model()

    days = data["days"]
    students = data["students"]

    open_hours_per_day = data["open_hours_per_day"]
    max_students_per_day = data["max_students_per_day"]
    max_shifts_per_week = data["max_shifts_per_week"]
    min_week_undergrad = data["minimum_weekly_hours_undergrad"]
    min_week_grad = data["minimum_weekly_hours_grad"]

    undergrads = data["undergraduates"]
    grads = data["graduates"]

    # Wage per hour for each student (keys are strings; convert to int)
    wage = {int(k): v for k, v in data["wage"].items()}

    # Availability hours per student per day
    avail_per_student = {}
    for i in students:
        avail_per_student[i] = data["availability_hours"][str(i)]

    # Variables dictionary: keys must be exactly as specified
    variables = {}

    # Hours variables h_i_d (continuous)
    for i in students:
        for d in days:
            key_h = f"h_{i}_{d}"
            ub = avail_per_student[i][d]
            v = model.addVar(lb=0.0, ub=float(ub), vtype=GRB.CONTINUOUS, name=key_h)
            variables[key_h] = v

    # Binary shift indicator y_i_d
    for i in students:
        for d in days:
            key_y = f"y_{i}_{d}"
            v = model.addVar(vtype=GRB.BINARY, name=key_y)
            variables[key_y] = v

    # Objective: minimize total wage cost
    obj = gp.quicksum(wage[i] * variables[f"h_{i}_{d}"] for i in students for d in days)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1) Coverage: sum_i h_i_d == open_hours_per_day for each day
    for d in days:
        model.addConstr(gp.quicksum(variables[f"h_{i}_{d}"] for i in students) == open_hours_per_day,
                        name=f"cover_{d}")

    # 2) h_i_d <= availability_i_d * y_i_d (enforces y when there are hours)
    for i in students:
        for d in days:
            model.addConstr(variables[f"h_{i}_{d}"] <= avail_per_student[i][d] * variables[f"y_{i}_{d}"],
                            name=f"hours_y_{i}_{d}")

    # 3) No more than max_students_per_day students scheduled per day
    for d in days:
        model.addConstr(gp.quicksum(variables[f"y_{i}_{d}"] for i in students) <= max_students_per_day,
                        name=f"max3_{d}")

    # 4) No more than max_shifts_per_week per student
    for i in students:
        model.addConstr(gp.quicksum(variables[f"y_{i}_{d}"] for d in days) <= max_shifts_per_week,
                        name=f"maxshift_{i}")

    # 5) Minimum weekly hours per student (undergraduates)
    for i in undergrads:
        model.addConstr(gp.quicksum(variables[f"h_{i}_{d}"] for d in days) >= min_week_undergrad,
                        name=f"minH_under_{i}")

    # 6) Minimum weekly hours per student (graduates)
    for i in grads:
        model.addConstr(gp.quicksum(variables[f"h_{i}_{d}"] for d in days) >= min_week_grad,
                        name=f"minH_grad_{i}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    # Build model, then optimize, and return the required solution schema
    model, variables = build_model(data)
    model.update()
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    # Build solution dict in the exact order and keys required
    solution = {}
    days = data["days"]
    students = data["students"]

    for i in students:
        for d in days:
            solution[f"h_{i}_{d}"] = float(variables[f"h_{i}_{d}"].X)
    for i in students:
        for d in days:
            solution[f"y_{i}_{d}"] = float(variables[f"y_{i}_{d}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }