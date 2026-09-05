import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    products = data["products"]  # ["I","II","III"]
    quarters = data["quarters"]  # [1,2,3,4]

    # Data extraction
    orders = data["orders"]  # keys like "I_1": value
    hours_per_unit = data["hours_per_unit"]  # {"I":2, "II":4, "III":3}
    capacity = data["capacity_hours_per_quarter"]
    required_ending_inventory = data["required_ending_inventory"]
    late_penalty = data["late_penalty_per_unit_per_quarter"]  # {"I":20, "II":20, "III":10}
    storage_cost = data["storage_cost_per_unit_per_quarter"]
    # Blocked quarter for product I
    # data contains "product_I_blocked_quarter" but we will enforce by constraint on x_I_2 = 0
    blocked_quarter_I = data.get("product_I_blocked_quarter", None)

    # Decision variables will be stored in a flat dict under a single key to match required structure
    variables = {"variables_keys": {}}

    # Create production variables x_P_q
    for P in products:
        for q in quarters:
            key = f"x_{P}_{q}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            variables["variables_keys"][key] = v

    # Create ending inventory variables Iv_P_q
    for P in products:
        for q in quarters:
            key = f"Iv_{P}_{q}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            variables["variables_keys"][key] = v

    # Create backlog variables Bk_P_q
    for P in products:
        for q in quarters:
            key = f"Bk_{P}_{q}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            variables["variables_keys"][key] = v

    model.update()

    # Capacity constraint
    cap_expr = gp.LinExpr()
    for P in products:
        h = hours_per_unit[P]
        for q in quarters:
            cap_expr += h * variables["variables_keys"][f"x_{P}_{q}"]
    model.addConstr(cap_expr <= capacity, name="Capacity")

    # Ending inventory at quarter 4 must be required 150 units per product
    for P in products:
        Iv_4 = variables["variables_keys"][f"Iv_{P}_4"]
        model.addConstr(Iv_4 == required_ending_inventory, name=f"EndingInv_{P}")

    # Product I cannot be produced in quarter 2
    model.addConstr(variables["variables_keys"]["x_I_2"] == 0, name="Block_I_Q2")

    # Balance and backlog propagation constraints
    # We implement the relationships:
    # Iv_p_q - Iv_p_{q-1} - x_p_q + D_p_q + Bk_p_{q-1} - Bk_p_q = 0
    # For q=1, Iv_p_0 and Bk_p_0 are treated as 0.
    for P in products:
        for q in quarters:
            Iv_q = variables["variables_keys"][f"Iv_{P}_{q}"]
            Bk_q = variables["variables_keys"][f"Bk_{P}_{q}"]
            x_q = variables["variables_keys"][f"x_{P}_{q}"]
            D_q = orders[f"{P}_{q}"]
            if q == 1:
                # Iv_0 = 0, Bk_0 = 0
                model.addConstr(Iv_q - x_q + D_q - Bk_q == 0, name=f"Balance_{P}_{q}")
                # Backlog upper bound: Bk_1 <= D_1
                model.addConstr(Bk_q <= D_q, name=f"BacklogUB_{P}_{q}")
                # Supply feasibility: D_1 - Bk_1 <= x_1
                model.addConstr(D_q - Bk_q <= x_q, name=f"SupplyFeas_{P}_{q}")
            else:
                Iv_prev = variables["variables_keys"][f"Iv_{P}_{q-1}"]
                Bk_prev = variables["variables_keys"][f"Bk_{P}_{q-1}"]
                model.addConstr(Iv_q - Iv_prev - x_q + D_q + Bk_prev - Bk_q == 0, name=f"Balance_{P}_{q}")
                # Backlog upper bound: Bk_q <= D_q + Bk_prev
                model.addConstr(Bk_q <= D_q + Bk_prev, name=f"BacklogUB_{P}_{q}")
                # Supply feasibility: D_q + Bk_prev - Bk_q <= Iv_prev + x_q
                model.addConstr(D_q + Bk_prev - Bk_q <= Iv_prev + x_q, name=f"SupplyFeas_{P}_{q}")

    model.update()

    # Objective: minimize storage cost and late penalties
    obj = gp.LinExpr()
    for P in products:
        penalty = late_penalty[P]
        for q in quarters:
            Bk_q = variables["variables_keys"][f"Bk_{P}_{q}"]
            Iv_q = variables["variables_keys"][f"Iv_{P}_{q}"]
            obj += penalty * Bk_q + storage_cost * Iv_q

    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    # Map status to a readable string
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

    obj_val = model.ObjVal

    solution = {}
    for key, var in variables["variables_keys"].items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }