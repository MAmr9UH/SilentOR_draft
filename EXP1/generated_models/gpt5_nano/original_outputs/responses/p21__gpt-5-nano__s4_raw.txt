import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    days = data["days"]
    demand = data["demand"]
    n = len(days)

    starts = ["start_Monday","start_Tuesday","start_Wednesday","start_Thursday","start_Friday","start_Saturday","start_Sunday"]
    day_names = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    variables = {}
    for i, day_name in enumerate(day_names):
        var_name = starts[i]
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=var_name)
        variables[var_name] = v

    model.update()

    for j, day_name in enumerate(days):
        expr = gp.quicksum(variables[starts[s]] for s in range(n) if ((j - s) % n) <= 4)
        model.addConstr(expr >= demand[day_name], name=f"cover_{day_name}")

    model.setObjective(gp.quicksum(variables[starts[s]] for s in range(n)), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(int(model.Status), str(model.Status))
    objective = float(model.ObjVal)

    solution = {}
    for key in ["start_Monday","start_Tuesday","start_Wednesday","start_Thursday","start_Friday","start_Saturday","start_Sunday"]:
        solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }