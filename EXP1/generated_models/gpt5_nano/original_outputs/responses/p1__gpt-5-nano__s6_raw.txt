import itertools
from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]

    n = len(cap)
    M = sum(dem)

    model = Model()

    # Decision variables
    produced = {}
    for i in range(1, n + 1):
        produced[str(i)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i}")

    allocation = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                allocation[f"{i},{j}"] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i}_{j}")

    z = {}
    for i in range(1, n + 1):
        z[str(i)] = model.addVar(vtype=GRB.BINARY, name=f"z_{i}")

    model.update()

    # Constraints
    # 1) Demand satisfaction: sum_i allocation[i,j] == dem_j
    for j in range(1, n + 1):
        alloc_terms = []
        for i in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                alloc_terms.append(allocation[f"{i},{j}"])
        model.addConstr(quicksum(alloc_terms) == dem[j - 1], name=f"demand_{j}")

    # 2) Link allocations to production: sum_j allocation[i,j] <= produced_i
    for i in range(1, n + 1):
        terms = []
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                terms.append(allocation[f"{i},{j}"])
        model.addConstr(quicksum(terms) <= produced[str(i)], name=f"prod_cover_{i}")

    # 3) Fixed charge linkage: produced_i <= M * z_i
    for i in range(1, n + 1):
        model.addConstr(produced[str(i)] <= M * z[str(i)], name=f"fixed_link_{i}")

    # Objective: minimize variable costs + fixed costs
    var_cost_term = quicksum(vcost[i - 1] * produced[str(i)] for i in range(1, n + 1))
    fixed_cost_term = fixed * quicksum(z[str(i)] for i in range(1, n + 1))
    model.setObjective(var_cost_term + fixed_cost_term, GRB.MINIMIZE)

    model.update()

    variables = {
        "produced": produced,
        "allocation": allocation
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    produced_solution = {k: float(v.X) for k, v in variables["produced"].items()}
    allocation_solution = {}
    for k, v in variables["allocation"].items():
        allocation_solution[k] = float(v.X)

    solution = {
        "produced": produced_solution,
        "allocation": allocation_solution
    }

    result = {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }

    return result