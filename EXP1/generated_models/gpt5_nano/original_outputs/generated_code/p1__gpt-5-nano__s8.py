import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed_cost = data["fixed"]

    n = len(cap)
    total_demand = sum(dem)
    M = total_demand

    model = gp.Model()

    # Decision variables
    produced = {str(i): model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{i}") for i in range(1, n+1)}

    allocation = {}
    for i in range(1, n+1):
        for j in range(1, n+1):
            if cap[i-1] >= cap[j-1]:
                allocation[f"{i},{j}"] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"a_{i}_{j}")

    y = {i: model.addVar(vtype=GRB.BINARY, name=f"y_{i}") for i in range(1, n+1)}

    model.update()

    # Demand constraints: sum_i a_{i,j} == dem_j
    for j in range(1, n+1):
        expr = gp.quicksum([allocation[f"{i},{j}"] for i in range(1, n+1) if cap[i-1] >= cap[j-1]])
        model.addConstr(expr == dem[j-1], name=f"demand_{j}")

    # Allocation usage: sum_j a_{i,j} <= x_i
    for i in range(1, n+1):
        expr = gp.quicksum([allocation[f"{i},{j}"] for j in range(1, n+1) if cap[i-1] >= cap[j-1]])
        model.addConstr(expr <= produced[str(i)], name=f"alloc_prod_{i}")

    # Coupling: x_i <= M * y_i
    for i in range(1, n+1):
        model.addConstr(produced[str(i)] <= M * y[i], name=f"prod_fixed_{i}")

    # Objective: minimize fixed costs + variable costs on allocations
    fixed_term = gp.quicksum([fixed_cost * y[i] for i in range(1, n+1)])
    var_term = gp.quicksum(
        [vcost[i-1] * allocation[f"{i},{j}"]
         for i in range(1, n+1) for j in range(1, n+1)
         if cap[i-1] >= cap[j-1]]
    )
    model.setObjective(fixed_term + var_term, GRB.MINIMIZE)

    variables = {
        "produced": produced,
        "allocation": allocation
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CUTOFF: "CUTOFF"
    }
    status_str = status_map.get(status, str(status))

    model.update()

    # Extract produced quantities
    produced_result = {}
    for i in range(1, len(data["cap"]) + 1):
        key = str(i)
        produced_result[key] = float(variables["produced"][key].X)

    # Extract allocations
    allocation_result = {}
    for key in sorted(variables["allocation"].keys(), key=lambda s: (int(s.split(',')[0]), int(s.split(',')[1]))):
        allocation_result[key] = float(variables["allocation"][key].X)

    solution = {
        "produced": produced_result,
        "allocation": allocation_result
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }