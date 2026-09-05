import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    days = data.get("days", [])
    n = len(days)
    demands = [0] * n
    for i, d in enumerate(days):
        demands[i] = data.get("demand", {}).get(d, 0)

    model = gp.Model()

    day_keys = [
        "start_Monday",
        "start_Tuesday",
        "start_Wednesday",
        "start_Thursday",
        "start_Friday",
        "start_Saturday",
        "start_Sunday",
    ]

    # Create decision variables
    vars_map = {}
    for key in day_keys:
        var = model.addVar(vtype=GRB.INTEGER, name=key, lb=0)
        vars_map[key] = var

    # Constraints: for each day, demand equals sum of starts of that day and previous 4 days
    for i in range(n):
        window_idx = [(i - k) % n for k in range(5)]
        expr = gp.quicksum(vars_map[day_keys[j]] for j in window_idx)
        model.addConstr(expr == demands[i], name=f"Demand_{days[i]}")

    # Objective: minimize total number of workers
    model.setObjective(gp.quicksum(vars_map[key] for key in day_keys), GRB.MINIMIZE)

    # Prepare return variable dictionary with exact keys
    variables = {
        "start_Monday": vars_map["start_Monday"],
        "start_Tuesday": vars_map["start_Tuesday"],
        "start_Wednesday": vars_map["start_Wednesday"],
        "start_Thursday": vars_map["start_Thursday"],
        "start_Friday": vars_map["start_Friday"],
        "start_Saturday": vars_map["start_Saturday"],
        "start_Sunday": vars_map["start_Sunday"],
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    def status_to_string(s):
        if s == GRB.OPTIMAL:
            return "OPTIMAL"
        if s == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if s == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if s == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if s == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        return str(s)

    status_str = status_to_string(model.Status)
    objective_value = float(model.ObjVal)

    solution = {}
    for key in [
        "start_Monday",
        "start_Tuesday",
        "start_Wednesday",
        "start_Thursday",
        "start_Friday",
        "start_Saturday",
        "start_Sunday",
    ]:
        solution[key] = int(round(variables[key].X))

    result = {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": {
            "start_Monday": solution["start_Monday"],
            "start_Tuesday": solution["start_Tuesday"],
            "start_Wednesday": solution["start_Wednesday"],
            "start_Thursday": solution["start_Thursday"],
            "start_Friday": solution["start_Friday"],
            "start_Saturday": solution["start_Saturday"],
            "start_Sunday": solution["start_Sunday"],
        }
    }

    return result