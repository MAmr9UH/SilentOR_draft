import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model('lab_schedule')

    days = data["days"]          # e.g., ["Mon","Tue","Wed","Thu"," Fri"]
    students = data["students"]  # e.g., [1,2,3,4,5,6]

    wage = data["wage"]                          # dict with string keys "1".."6"
    availability_hours = data["availability_hours"]  # dict of dicts, keys "1".."6" -> {"Mon": val, ...}
    open_hours = data["open_hours_per_day"]       # e.g., 14

    min_undergrad = data["minimum_weekly_hours_undergrad"]
    min_grad = data["minimum_weekly_hours_grad"]
    max_shifts = data["max_shifts_per_week"]
    max_students_day = data["max_students_per_day"]

    undergrads = data["undergraduates"]  # e.g., [1,2,3,4]
    grads = data["graduates"]            # e.g., [5,6]

    # Decision variables
    h = {}  # continuous: hours of student i on day d
    y = {}  # binary: whether student i is scheduled on day d

    for i in students:
        for d in days:
            h[(i, d)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=open_hours, name=f'h_{i}_{d}')
            y[(i, d)] = model.addVar(vtype=GRB.BINARY, name=f'y_{i}_{d}')

    # Constraints

    # 1) Each day must have open_hours hours of coverage from all students
    for d in days:
        model.addConstr(gp.quicksum(h[(i, d)] for i in students) == open_hours, name=f'cover_{d}')

    # 2) Per-student per-day availability and linking hours to scheduling
    for i in students:
        i_str = str(i)
        for d in days:
            avail = availability_hours[i_str][d]
            model.addConstr(h[(i, d)] <= avail, name=f'avail_{i}_{d}')
            model.addConstr(h[(i, d)] <= open_hours * y[(i, d)], name=f'link_{i}_{d}')

    # 3) Weekly minimum hours per student
    for i in students:
        total_hours = gp.quicksum(h[(i, d)] for d in days)
        if i in undergrads:
            model.addConstr(total_hours >= min_undergrad, name=f'min_undergrad_{i}')
        elif i in grads:
            model.addConstr(total_hours >= min_grad, name=f'min_grad_{i}')

    # 4) Max shifts per week per student
    for i in students:
        model.addConstr(gp.quicksum(y[(i, d)] for d in days) <= max_shifts, name=f'max_shifts_{i}')

    # 5) Max number of distinct students per day
    for d in days:
        model.addConstr(gp.quicksum(y[(i, d)] for i in students) <= max_students_day, name=f'max_students_{d}')

    # Objective: minimize gross pay
    objective = gp.quicksum(wage[str(i)] * h[(i, d)] for i in students for d in days)
    model.setObjective(objective, GRB.MINIMIZE)

    # Collect variables into the required flat dict
    variables = {}
    for i in students:
        for d in days:
            variables[f'h_{i}_{d}'] = h[(i, d)]
            variables[f'y_{i}_{d}'] = y[(i, d)]

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    # Build solution dict with all variable values
    solution = {}
    days = data["days"]
    for i in data["students"]:
        for d in days:
            solution[f'h_{i}_{d}'] = float(variables[f'h_{i}_{d}'].X)
            solution[f'y_{i}_{d}'] = float(variables[f'y_{i}_{d}'].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }