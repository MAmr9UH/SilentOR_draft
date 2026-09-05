import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    caps = data["cap"]
    dems = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]

    n = len(caps)
    model = gp.Model()

    # Allocation variables: only for i,j where cap_i >= cap_j
    allocation = {}
    for i in range(1, n+1):
        for j in range(1, n+1):
            if caps[i-1] >= caps[j-1]:
                v = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"x_{i}_{j}")
                allocation[(i, j)] = v

    # Produced indicator variables: binary (whether type i is used)
    produced = {}
    for i in range(1, n+1):
        produced[str(i)] = model.addVar(vtype=GRB.BINARY, name=f"p_{i}")

    model.update()

    # Objective: fixed cost for each used type + variable cost for allocations
    obj = gp.LinExpr()
    for i in range(1, n+1):
        obj += fixed * produced[str(i)]
    for (i, j), var in allocation.items():
        obj += vcost[i-1] * var
    model.setObjective(obj, GRB.MINIMIZE)

    # Demand satisfaction constraints: for each demand j, sum_i allocation_{i,j} == dem_j
    for j in range(1, n+1):
        alloc_sum = gp.quicksum(allocation[(i, j)] for i in range(1, n+1) if (i, j) in allocation)
        model.addConstr(alloc_sum == dems[j-1], name=f"demand_{j}")

    # Fixed-cost linking constraints: sum_j allocation_{i,j} <= BIG_M * produced_i
    # and sum_j allocation_{i,j} >= produced_i to ensure produced_i=1 iff there is allocation from i
    BIG_M = sum(dems)
    for i in range(1, n+1):
        alloc_row = gp.quicksum(allocation[(i, j)] for j in range(1, n+1) if (i, j) in allocation)
        model.addConstr(alloc_row <= BIG_M * produced[str(i)], name=f"link_upper_{i}")
        model.addConstr(alloc_row >= produced[str(i)], name=f"link_lower_{i}")

    model.update()

    variables = {
        "produced": {str(i): produced[str(i)] for i in range(1, n+1)},
        "allocation": {f"{i},{j}": allocation[(i, j)] for (i, j) in allocation}
    }

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build produced and allocation outputs from the solved model
    n = len(data["cap"])
    produced_out = {}
    for i in range(1, n+1):
        # units produced of type i is the sum of allocations from i
        s = 0
        for j in range(1, n+1):
            key = f"{i},{j}"
            if key in variables["allocation"]:
                s += variables["allocation"][key].X
        produced_out[str(i)] = int(round(s))

    allocation_out = {}
    for key, var in variables["allocation"].items():
        allocation_out[key] = int(round(var.X))

    solution = {
        "produced": produced_out,
        "allocation": allocation_out
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }