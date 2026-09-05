from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    model = Model()
    days = data["days"]
    students = data["students"]
    open_hours = data["open_hours_per_day"]
    undergrads = data["undergraduates"]
    all_grads = [s for s in students if s not in undergrads]

    wages = data["wage"]
    availability = data["availability_hours"]

    # Dictionaries to hold variables (flat keys as required)
    variables = {}

    # Create variables
    h_vars = {}  # (i, d) -> Var
    y_vars = {}  # (i, d) -> Var

    for i in students:
        for d in days:
            avail = availability[str(i)][d]
            h = model.addVar(lb=0, ub=avail, vtype=GRB.CONTINUOUS, name=f"h_{i}_{d}")
            y = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{d}")
            h_vars[(i, d)] = h
            y_vars[(i, d)] = y
            variables[f"h_{i}_{d}"] = h
            variables[f"y_{i}_{d}"] = y
            # Linking hours to schedule (if not scheduled, hours must be 0)
            model.addConstr(h <= avail * y)

    # Day-level constraints: exactly open_hours total hours per day,
    # and exactly one student scheduled per day, with at most 3 allowed (redundant but included)
    for d in days:
        model.addConstr(quicksum(h_vars[(i, d)] for i in students) == open_hours, name=f"open_{d}")
        model.addConstr(quicksum(y_vars[(i, d)] for i in students) == 1, name=f"single_{d}")
        model.addConstr(quicksum(y_vars[(i, d)] for i in students) <= 3, name=f"max3_{d}")

    # Weekly minimum hours per student
    min_undergrad = data["minimum_weekly_hours_undergrad"]
    min_grad = data["minimum_weekly_hours_grad"]

    for i in undergrads:
        model.addConstr(quicksum(h_vars[(i, d)] for d in days) >= min_undergrad, name=f"minundergrad_{i}")

    for i in all_grads:
        model.addConstr(quicksum(h_vars[(i, d)] for d in days) >= min_grad, name=f"mingrad_{i}")

    # Maximum shifts per week
    max_shifts = data["max_shifts_per_week"]
    for i in students:
        model.addConstr(quicksum(y_vars[(i, d)] for d in days) <= max_shifts, name=f"maxshifts_{i}")

    # Objective: minimize gross pay = sum wage_i * hours
    model.setObjective(
        quicksum( ( wages[str(i)] * h_vars[(i, d)] ) for i in students for d in days ),
        GRB.MINIMIZE
    )

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    # Prepare status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Objective value
    obj_val = float(model.ObjVal) if model.SolCount > 0 else None

    # Solution dictionary: include all h_i_d and y_i_d
    solution = {}
    for i in data["students"]:
        for d in data["days"]:
            h_key = f"h_{i}_{d}"
            y_key = f"y_{i}_{d}"
            solution[h_key] = float(variables[h_key].X)
            solution[y_key] = float(variables[y_key].X)

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }