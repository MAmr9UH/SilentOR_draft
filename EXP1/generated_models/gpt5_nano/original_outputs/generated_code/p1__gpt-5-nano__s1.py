import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]

    n = len(cap)
    M = sum(dem)

    model = gp.Model()

    # Decision variables
    produced = {}
    for i in range(1, n + 1):
        produced[str(i)] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i}")

    allocation = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                allocation[f"{i},{j}"] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i}_{j}")

    # Optional binary indicators for fixed costs (not exposed in the return structure)
    y = {}
    for i in range(1, n + 1):
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")

    model.update()

    # Demand constraints: satisfy or exceed each demand using available allocations
    for j in range(1, n + 1):
        alloc_sum = gp.quicksum(allocation[f"{i},{j}"] for i in range(1, n + 1) if f"{i},{j}" in allocation)
        model.addConstr(alloc_sum >= dem[j - 1], name=f"Demand_{j}")

    # Capacity constraints: total allocations from a type cannot exceed its production
    for i in range(1, n + 1):
        alloc_from_i = gp.quicksum(allocation[f"{i},{j}"] for j in range(1, n + 1) if f"{i},{j}" in allocation)
        model.addConstr(alloc_from_i <= produced[str(i)], name=f"Cap_from_{i}")

    # Link produced quantities to the binary indicators (fixed costs)
    for i in range(1, n + 1):
        model.addConstr(produced[str(i)] <= M * y[i], name=f"FixedLink_{i}")

    # Objective: minimize production variable costs plus fixed costs
    objective = gp.quicksum(vcost[i - 1] * produced[str(i)] for i in range(1, n + 1)) + fixed * gp.quicksum(y[i] for i in range(1, n + 1))
    model.setObjective(objective, GRB.MINIMIZE)

    variables = {
        "produced": produced,
        "allocation": allocation
    }

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map numeric status to string
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

    objective = model.ObjVal

    # Read produced values
    produced_sol = {}
    for i in range(1, len(data["cap"]) + 1):
        produced_sol[str(i)] = int(variables["produced"][str(i)].X)

    # Read allocation values (only for i,j with cap_i >= cap_j)
    allocation_sol = {}
    for key, var in variables["allocation"].items():
        allocation_sol[key] = int(var.X)

    solution = {
        "produced": produced_sol,
        "allocation": allocation_sol
    }

    return {
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }