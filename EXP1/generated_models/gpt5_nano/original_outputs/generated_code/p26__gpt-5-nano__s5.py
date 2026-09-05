import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    days = data["days"]
    open_hours = data["open_hours_per_day"]
    max_shifts = data["max_shifts_per_week"]
    min_undergrad = data["minimum_weekly_hours_undergrad"]
    min_grad = data["minimum_weekly_hours_grad"]

    students = data["students"]
    undergrads = set(map(int, data["undergraduates"]))
    grads = set(map(int, data["graduates"]))

    wages = {int(k): float(v) for k, v in data["wage"].items()}
    avail = data["availability_hours"]  # keys are strings of student ids

    h = {}
    y = {}

    # Create decision variables
    for i in students:
        for d in days:
            h_key = f"h_{i}_{d}"
            y_key = f"y_{i}_{d}"
            # Hours worked by student i on day d
            h[(i, d)] = model.addVar(lb=0.0, ub=open_hours, vtype=GRB.CONTINUOUS, name=h_key)
            # Whether student i is scheduled for a shift on day d (binary)
            y[(i, d)] = model.addVar(vtype=GRB.BINARY, name=y_key)

    model.update()

    # Objective: minimize total gross pay
    obj = gp.quicksum(wages[i] * h[(i, d)] for i in students for d in days)
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints

    # 1) Exactly open_hours of coverage each day (sum of hours across all students equals open_hours)
    for d in days:
        model.addConstr(gp.quicksum(h[(i, d)] for i in students) == open_hours, name=f"cover_{d}")

    # 2) No more than 3 students scheduled per day
    for d in days:
        model.addConstr(gp.quicksum(y[(i, d)] for i in students) <= 3, name=f"max_workers_{d}")

    # 3) Hours limited by availability and linked to whether scheduled
    for i in students:
        for d in days:
            avail_i_d = float(avail[str(i)][d])
            model.addConstr(h[(i, d)] <= avail_i_d, name=f"avail_{i}_{d}")
            model.addConstr(h[(i, d)] <= open_hours * y[(i, d)], name=f"link_{i}_{d}")

    # 4) Weekly minimum hours per student
    for i in students:
        total_hours = gp.quicksum(h[(i, d)] for d in days)
        if int(i) in undergrads:
            model.addConstr(total_hours >= min_undergrad, name=f"min_undergrad_{i}")
        else:
            model.addConstr(total_hours >= min_grad, name=f"min_grad_{i}")

    # 5) Maximum shifts per week
    for i in students:
        total_shifts = gp.quicksum(y[(i, d)] for d in days)
        model.addConstr(total_shifts <= max_shifts, name=f"max_shifts_{i}")

    # Prepare return structure: flat dict of all variables with exact keys
    variables = {}
    for i in students:
        for d in days:
            h_key = f"h_{i}_{d}"
            y_key = f"y_{i}_{d}"
            variables[h_key] = h[(i, d)]
            variables[y_key] = y[(i, d)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.update()
    model.optimize()
    # Map status to human-readable string using allowed GRB constants
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    obj = float(model.ObjVal)

    # Read solution values
    solution = {}
    for key, var in variables.items():
        try:
            solution[key] = float(var.X)
        except:
            solution[key] = None

    return {
        "status": status,
        "objective": obj,
        "solution": solution
    }