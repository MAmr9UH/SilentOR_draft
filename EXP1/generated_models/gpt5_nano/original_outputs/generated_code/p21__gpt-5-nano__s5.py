def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model()

    # Decision variables: number of workers whose 5-day stretch starts on each day
    start_Monday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Monday")
    start_Tuesday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Tuesday")
    start_Wednesday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Wednesday")
    start_Thursday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Thursday")
    start_Friday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Friday")
    start_Saturday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Saturday")
    start_Sunday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Sunday")

    variables = [
        start_Monday,
        start_Tuesday,
        start_Wednesday,
        start_Thursday,
        start_Friday,
        start_Saturday,
        start_Sunday
    ]

    # Map days to indices
    days = data["days"]  # ["Monday", "Tuesday", ..., "Sunday"]
    demand_by_name = data["demand"]
    demand_list = [demand_by_name[day] for day in days]

    work_days = int(data["work_consecutive_days"])  # 5

    # Coverage: which days are covered by a worker starting on day i
    coverage = []
    for i in range(7):
        cov = set((i + k) % 7 for k in range(work_days))
        coverage.append(cov)

    # Constraints: meet demand on each day
    for j in range(7):
        lhs = gp.quicksum(variables[i] for i in range(7) if j in coverage[i])
        model.addConstr(lhs >= demand_list[j], name=f"cover_day_{days[j]}")

    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(variables), GRB.MINIMIZE)

    model.update()

    # Return the model and the required variables dict
    return model, {
        "start_Monday": start_Monday,
        "start_Tuesday": start_Tuesday,
        "start_Wednesday": start_Wednesday,
        "start_Thursday": start_Thursday,
        "start_Friday": start_Friday,
        "start_Saturday": start_Saturday,
        "start_Sunday": start_Sunday
    }


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string
    status_code = model.Status
    if status_code == 0:  # OPTIMAL
        status = "OPTIMAL"
    elif status_code == 1:  # INFEASIBLE
        status = "INFEASIBLE"
    elif status_code == 2:  # INF_OR_UNBD
        status = "INF_OR_UNBD"
    elif status_code == 3:  # FACT_PUL
        status = "UNBOUNDED"  # This case is not standard; keep as a fallback
    elif status_code == 4:  # TIME_LIMIT
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    # Read solution values
    sol = {
        "start_Monday": int(round(variables["start_Monday"].X)),
        "start_Tuesday": int(round(variables["start_Tuesday"].X)),
        "start_Wednesday": int(round(variables["start_Wednesday"].X)),
        "start_Thursday": int(round(variables["start_Thursday"].X)),
        "start_Friday": int(round(variables["start_Friday"].X)),
        "start_Saturday": int(round(variables["start_Saturday"].X)),
        "start_Sunday": int(round(variables["start_Sunday"].X))
    }

    return {
        "status": status,
        "objective": objective,
        "solution": sol
    }