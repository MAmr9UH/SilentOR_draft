import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    days = data["days"]
    n = len(days)

    # Build demand vector in the given day order
    demand = [data["demand"][day] for day in days]

    # Create model
    model = gp.Model()

    # Decision variables: number of workers starting on each day
    starts = {}
    for day in days:
        var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"start_{day}")
        starts[day] = var

    model.update()

    # Constraints: for each day, sum of starting groups that cover that day equals demand
    for i, day_i in enumerate(days):
        expr = gp.LinExpr()
        for j, day_j in enumerate(days):
            diff = (i - j) % n
            if diff <= 4:  # a 5-day work window covers this day
                expr += starts[day_j]
        model.addConstr(expr == demand[i], name=f"cover_{day_i}")

    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(starts[day] for day in days), GRB.MINIMIZE)

    # Prepare variables dict with exact required keys
    variables = {f"start_{day}": starts[day] for day in days}

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_code, str(status_code))

    objective_value = None
    if model.ObjVal is not None:
        objective_value = float(model.ObjVal)

    solution = {}
    for key in ["start_Monday", "start_Tuesday", "start_Wednesday", "start_Thursday", "start_Friday", "start_Saturday", "start_Sunday"]:
        solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }