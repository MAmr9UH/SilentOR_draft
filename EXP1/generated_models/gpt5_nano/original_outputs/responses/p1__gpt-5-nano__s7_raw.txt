import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed_cost = data["fixed"]

    n = len(cap)
    M = sum(dem)

    model = gp.Model()

    # Decision variables
    produced = {str(i+1): model.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i+1}") for i in range(n)}

    allocation = {}
    for i in range(n):
        for j in range(n):
            if cap[i] >= cap[j]:
                key = f"{i+1},{j+1}"
                allocation[key] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"a_{i+1}_{j+1}")

    y = [model.addVar(vtype=GRB.BINARY, name=f"y_{i+1}") for i in range(n)]

    model.update()

    # Constraints
    # 1) Demand satisfaction: sum_i allocation_{i,j} == dem_j
    for j in range(n):
        expr = gp.quicksum(allocation[f"{i+1},{j+1}"] for i in range(n) if cap[i] >= cap[j])
        model.addConstr(expr == dem[j], name=f"demand_{j+1}")

    # 2) Link produced to allocations: produced_i == sum_j allocation_{i,j}
    for i in range(n):
        expr = gp.quicksum(allocation[f"{i+1},{j+1}"] for j in range(n) if cap[i] >= cap[j])
        model.addConstr(produced[str(i+1)] == expr, name=f"prod_alloc_link_{i+1}")

    # 3) Fixed cost modeling: produced_i <= M * y_i, produced_i >= y_i
    for i in range(n):
        model.addConstr(produced[str(i+1)] <= M * y[i], name=f"prod_y_upper_{i+1}")
        model.addConstr(produced[str(i+1)] >= y[i], name=f"prod_y_lower_{i+1}")

    # Objective: Minimize variable production cost + fixed costs
    objective = gp.quicksum(vcost[i] * produced[str(i+1)] for i in range(n)) + fixed_cost * gp.quicksum(y)
    model.setObjective(objective, GRB.MINIMIZE)

    model.update()

    variables = {
        "produced": {str(i+1): produced[str(i+1)] for i in range(n)},
        "allocation": {f"{i+1},{j+1}": allocation[f"{i+1},{j+1}"] for i in range(n) for j in range(n) if cap[i] >= cap[j]}
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    obj_val = float(model.ObjVal)

    produced_vals = {}
    for k in sorted(variables["produced"].keys(), key=lambda x: int(x)):
        produced_vals[k] = int(round(variables["produced"][k].X))

    allocation_vals = {}
    # sort keys for stable output
    for key in sorted(variables["allocation"].keys(), key=lambda s: (int(s.split(",")[0]), int(s.split(",")[1]))):
        allocation_vals[key] = int(round(variables["allocation"][key].X))

    solution = {
        "produced": produced_vals,
        "allocation": allocation_vals
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution,
        "note": "If a tested model returns 'produced' but omits 'allocation', treat as a schema/loud failure (the allocation field is required to validate the solution). A feasibility-based fallback (R1.C2) can be added later."
    }