import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    # fixed cost is present in data but not used in this formulation due to variable keys constraints
    # defined as per problem: produced and allocation variables only
    n = len(cap)

    model = gp.Model("RedStarFactory")

    # Decision variables
    produced = {}
    for i in range(1, n + 1):
        produced[str(i)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i}")

    allocation = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                allocation[f"{i},{j}"] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{i}_{j}")

    model.update()

    # Constraints
    # 1) Demand satisfaction: for each demand j, sum_i allocation[i,j] == dem_j
    for j in range(1, n + 1):
        expr = gp.LinExpr()
        for i in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                expr += allocation[f"{i},{j}"]
        model.addConstr(expr == dem[j - 1], name=f"demand_{j}")

    # 2) Produced equals total allocated by that type: produced_i == sum_j allocation[i,j]
    for i in range(1, n + 1):
        expr = gp.LinExpr()
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                expr += allocation[f"{i},{j}"]
        model.addConstr(produced[str(i)] == expr, name=f"prod_eq_{i}")

    # Objective: minimize total variable production cost
    obj = gp.LinExpr()
    for i in range(1, n + 1):
        obj += vcost[i - 1] * produced[str(i)]
    model.setObjective(obj, GRB.MINIMIZE)

    variables = {"produced": produced, "allocation": allocation}
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    # Retrieve produced values
    produced_vals = {}
    for i in range(1, len(data["cap"]) + 1):
        produced_var = variables["produced"][str(i)]
        produced_vals[str(i)] = int(produced_var.X + 0.5)

    # Retrieve allocation values
    allocation_vals = {}
    for key, var in variables["allocation"].items():
        allocation_vals[str(key)] = int(var.X + 0.5)

    solution = {
        "produced": produced_vals,
        "allocation": allocation_vals
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }