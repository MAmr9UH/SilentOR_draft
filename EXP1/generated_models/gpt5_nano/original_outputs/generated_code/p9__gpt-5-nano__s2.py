import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    days = len(data["employees_needed"])
    consecutive = int(data.get("work_days_consecutive", 5))
    demand = data["employees_needed"]

    model = gp.Model()

    # Create starting-day variables s0..s6 (7 days)
    variables = {}
    s_vars = []
    for i in range(days):
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{i}")
        s_vars.append(v)
        variables[f"s{i}"] = v

    model.update()

    # Coverage constraints: day i must be covered by workers started in the last 5 days
    for i in range(days):
        model.addConstr(
            quicksum(s_vars[(i - k) % days] for k in range(consecutive)) >= demand[i],
            name=f"cover_{i}"
        )

    # Objective: minimize total number of workers hired
    model.setObjective(quicksum(s_vars), GRB.MINIMIZE)

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
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.CUTOFF: "CUTOFF",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status = status_map.get(status_code, str(status_code))

    objective = model.ObjVal

    solution = {f"s{i}": variables[f"s{i}"].X for i in range(7)}

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }