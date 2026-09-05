import gurobipy as gp

def build_model(data: dict) -> tuple:
    days = data["days"]
    n = len(days)
    demand_list = [data["demand"][day] for day in days]
    work = data.get("work_consecutive_days", 5)

    model = gp.Model()

    # Create integer decision variables: number of workers starting on each day
    starts = {}
    for day in days:
        starts[day] = model.addVar(vtype=gp.GRB.INTEGER, name=f"start_{day}")

    model.update()

    # Constraints: on each day, sum of starts from that day and the previous (work-1) days >= demand
    for i, day in enumerate(days):
        expr = gp.quicksum(starts[days[(i - k) % n]] for k in range(work))
        model.addConstr(expr >= demand_list[i], name=f"need_{day}")

    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(starts[day] for day in days), gp.GRB.MINIMIZE)

    # Prepare variables dict with exact keys
    variables = {}
    for day in days:
        key = "start_" + day
        variables[key] = starts[day]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values for each start variable
    solution = {}
    for day in data["days"]:
        key = "start_" + day
        var = variables[key]
        solution[key] = int(round(var.X))

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }