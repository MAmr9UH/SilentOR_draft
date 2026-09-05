import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Extract data
    cap = list(data["cap"])
    dem = list(data["dem"])
    vcost = list(data["vcost"])
    fixed = data["fixed"]
    n = len(cap)
    total_dem = sum(dem)

    # Create model
    m = gp.Model()

    # Decision variables
    produced = {}
    for i in range(1, n + 1):
        produced[str(i)] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"produced_{i}")

    allocation = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if cap[i - 1] >= cap[j - 1]:
                allocation[f"{i},{j}"] = m.addVar(vtype=GRB.INTEGER, lb=0, name=f"alloc_{i}_{j}")

    # Binary open indicators (not exposed in output structure)
    open_i = {}
    for i in range(1, n + 1):
        open_i[i] = m.addVar(vtype=GRB.BINARY, name=f"open_{i}")

    m.update()

    # Constraints
    # 1) Demand satisfaction: sum_i allocation[i,j] == dem_j
    for j in range(1, n + 1):
        m.addConstr(
            gp.quicksum(allocation[f"{i},{j}"] for i in range(1, n + 1) if f"{i},{j}" in allocation) == dem[j - 1],
            name=f"Demand_{j}"
        )

    # 2) Production equals sum allocations per type
    for i in range(1, n + 1):
        m.addConstr(
            produced[str(i)] == gp.quicksum(allocation[f"{i},{j}"] for j in range(1, n + 1) if f"{i},{j}" in allocation),
            name=f"ProdSum_{i}"
        )

    # 3) Linking produced to binary indicators (enforce zero production if not opened)
    for i in range(1, n + 1):
        m.addConstr(produced[str(i)] <= total_dem * open_i[i], name=f"Link_{i}")

    # Objective: minimize variable costs + fixed costs for opened equipment
    obj = gp.LinExpr()
    for i in range(1, n + 1):
        obj += vcost[i - 1] * produced[str(i)]
        obj += fixed * open_i[i]
    m.setObjective(obj, GRB.MINIMIZE)

    m.update()

    variables = {
        "variables_keys": {
            "produced": produced,
            "allocation": allocation
        },
        "note": "indicator variables are optional; expose produced and allocation."
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    def _status_to_str(status: int) -> str:
        if status == GRB.OPTIMAL:
            return "OPTIMAL"
        if status == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if status == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if status == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if status == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        return str(status)

    status_str = _status_to_str(model.Status)
    obj_val = float(model.ObjVal)

    produced_vals = {k: float(v.X) for k, v in variables["variables_keys"]["produced"].items()}
    allocation_vals = {k: float(v.X) for k, v in variables["variables_keys"]["allocation"].items()}

    solution = {
        "produced": produced_vals,
        "allocation": allocation_vals
    }

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }