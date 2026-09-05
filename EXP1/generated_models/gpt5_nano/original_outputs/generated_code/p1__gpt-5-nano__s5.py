import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]

    n = len(cap)
    total_dem = sum(dem)
    M = total_dem  # big-M for linking produced with binary indicators

    m = gp.Model("RedStar")

    # Decision variables
    produced = {}
    for i in range(n):
        produced[str(i + 1)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i+1}")

    # Allocation variables: i -> j, only if cap[i] >= cap[j]
    alloc_vars = {}
    for i in range(n):
        for j in range(n):
            if cap[i] >= cap[j]:
                alloc_vars[(i + 1, j + 1)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i+1}_{j+1}")

    # Binary indicators for fixed cost
    y = {}
    for i in range(n):
        y[i + 1] = m.addVar(vtype=GRB.BINARY, name=f"y_{i+1}")

    m.update()

    # Objective: minimize production cost + fixed equipment cost
    obj = gp.LinExpr()
    for i in range(n):
        obj += vcost[i] * produced[str(i + 1)]
    for i in range(n):
        obj += fixed * y[i + 1]
    m.setObjective(obj, GRB.MINIMIZE)

    # Demand satisfaction constraints: sum_i allocation_{i,j} == dem_j
    for j in range(n):
        expr = gp.LinExpr()
        for i in range(n):
            if cap[i] >= cap[j]:
                expr += alloc_vars[(i + 1, j + 1)]
        m.addConstr(expr == dem[j], name=f"Demand_{j+1}")

    # Link produced to allocations: sum_j allocation_{i,j} == produced_i
    for i in range(n):
        expr = gp.LinExpr()
        for j in range(n):
            if cap[i] >= cap[j]:
                expr += alloc_vars[(i + 1, j + 1)]
        m.addConstr(expr == produced[str(i + 1)], name=f"ProduceLink_{i+1}")

    # Fixed cost constraints: produced_i <= M * y_i
    for i in range(n):
        m.addConstr(produced[str(i + 1)] <= M * y[i + 1], name=f"Fixed_{i+1}")

    m.update()

    # Prepare output-compatible variables dict
    produced_out = produced  # keys '1'..'n'
    allocation_by_key = {}
    for (ii, jj), var in alloc_vars.items():
        key = f"{ii},{jj}"
        allocation_by_key[key] = var

    variables = {
        "produced": produced_out,
        "allocation": allocation_by_key
    }

    return m, variables


def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Status string
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

    obj_val = float(model.ObjVal)

    # Produced results
    produced_result = {}
    for i in range(1, 7):
        produced_result[str(i)] = int(variables["produced"][str(i)].X)

    # Allocation results
    allocation_result = {}
    for key, var in variables["allocation"].items():
        allocation_result[key] = int(var.X)

    solution = {
        "produced": produced_result,
        "allocation": allocation_result
    }

    result = {
        "type": "object",
        "required": ["objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "reported optimal total cost"},
            "solution": {
                "type": "object",
                "required": ["produced", "allocation"],
                "properties": {
                    "produced": {"description": "units produced of each container type, keys '1'..'6'"},
                    "allocation": {"description": "units of type i used to satisfy demand class j; keys 'i,j' (1-indexed); include only i,j with capacity_i>=capacity_j"}
                }
            }
        },
        "note": "If a tested model returns 'produced' but omits 'allocation', treat as a schema/loud failure (the allocation field is required to validate the solution). A feasibility-based fallback (R1.C2) can be added later.",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }

    return result