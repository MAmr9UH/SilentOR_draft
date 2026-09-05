import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    products = data["products"]
    quarters = data["quarters"]

    # Demand mapping
    demand = {}
    for key, val in data["orders"].items():
        P, qstr = key.split("_")
        q = int(qstr)
        demand[(P, q)] = val

    hours_per_unit = data["hours_per_unit"]
    capacity = data["capacity_hours_per_quarter"]
    storage_cost = data["storage_cost_per_unit_per_quarter"]
    penalties = data["late_penalty_per_unit_per_quarter"]
    required_end_inventory = data["required_ending_inventory"]

    # Blocked quarter for product I (read from data if provided)
    blocked_quarter = data.get("product_I_blocked_quarter", 2)

    # Decision variables
    x = {}   # production
    Iv = {}  # ending inventory
    Bk = {}  # backlog

    variables = {}

    for P in products:
        for q in quarters:
            keyx = f"x_{P}_{q}"
            if P == "I" and q == blocked_quarter:
                v = model.addVar(lb=0.0, ub=0.0, name=keyx)
            else:
                v = model.addVar(lb=0.0, name=keyx)
            x[keyx] = v
            variables[keyx] = v

            keyIv = f"Iv_{P}_{q}"
            v_iv = model.addVar(lb=0.0, name=keyIv)
            Iv[keyIv] = v_iv
            variables[keyIv] = v_iv

            keyBk = f"Bk_{P}_{q}"
            v_bk = model.addVar(lb=0.0, name=keyBk)
            Bk[keyBk] = v_bk
            variables[keyBk] = v_bk

    model.update()

    # Production capacity constraints per quarter
    for q in quarters:
        expr = gp.quicksum(hours_per_unit[P] * x[f"x_{P}_{q}"] for P in products)
        model.addConstr(expr <= capacity, name=f"Cap_q{q}")

    # Flow constraints (inventory/backlog balance)
    for P in products:
        for q in quarters:
            keyx = f"x_{P}_{q}"
            keyIv = f"Iv_{P}_{q}"
            keyBk = f"Bk_{P}_{q}"
            if q == 1:
                d = demand[(P, 1)]
                model.addConstr(Iv[keyIv] - Bk[keyBk] - x[keyx] == -d, name=f"Flow_{P}_{q}")
            else:
                d = demand[(P, q)]
                model.addConstr(Iv[keyIv] - Bk[keyBk] - x[keyx] - Iv[f"Iv_{P}_{q-1}"] == -d, name=f"Flow_{P}_{q}")

    # End-of-quarter 4 inventory requirements
    for P in products:
        model.addConstr(Iv[f"Iv_{P}_4"] == required_end_inventory, name=f"EndInv_{P}")

    # Objective: minimize storage costs + late penalties
    obj = gp.LinExpr()
    for P in products:
        pen = penalties[P]
        for q in quarters:
            obj += storage_cost * Iv[f"Iv_{P}_{q}"] + pen * Bk[f"Bk_{P}_{q}"]
    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

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

    solution = {k: float(v.X) for k, v in variables.items()}

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }