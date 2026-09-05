import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Mapping of allowed (branch, specialty) per type i
    allowed_by_type = {
        1: [("Donghai", 1), ("Donghai", 2), ("Nanjiang", 1), ("Nanjiang", 2)],
        2: [("Donghai", 2), ("Donghai", 3), ("Nanjiang", 2), ("Nanjiang", 3)],
        3: [("Donghai", 1), ("Donghai", 3), ("Nanjiang", 1), ("Nanjiang", 3)],
        4: [("Donghai", 1), ("Donghai", 3), ("Nanjiang", 1), ("Nanjiang", 3)],
        5: [("Donghai", 2), ("Donghai", 3), ("Nanjiang", 2), ("Nanjiang", 3)],
        6: [("Donghai", 3), ("Nanjiang", 3)]
    }

    # Available people per type
    available = {i: int(data["available_people"][str(i)]) for i in range(1, 7)}

    # Create decision variables x_i_branch_s
    vars_by_key = {}
    # We'll also keep a flat list of keys to ensure exact output keys
    for i in range(1, 7):
        for (branch, spec) in allowed_by_type[i]:
            key = f"x_{i}_{branch}_{spec}"
            var = model.addVar(vtype=GRB.INTEGER, lb=0, ub=available[i], name=key)
            vars_by_key[key] = var

    # p3_shortfall variable
    p3_shortfall = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="p3_shortfall")

    model.update()

    # Demand constraints (P1 hard: fully meet all specialty demands)
    # Build demand values
    demand = data["demand"]
    demand_vals = {
        ("Donghai", 1): int(demand["Donghai_1"]),
        ("Donghai", 2): int(demand["Donghai_2"]),
        ("Donghai", 3): int(demand["Donghai_3"]),
        ("Nanjiang", 1): int(demand["Nanjiang_1"]),
        ("Nanjiang", 2): int(demand["Nanjiang_2"]),
        ("Nanjiang", 3): int(demand["Nanjiang_3"]),
    }

    for branch in ["Donghai", "Nanjiang"]:
        for spec in [1, 2, 3]:
            expr = gp.LinExpr()
            for i in range(1, 7):
                if (branch, spec) in allowed_by_type[i]:
                    key = f"x_{i}_{branch}_{spec}"
                    expr += vars_by_key[key]
            model.addConstr(expr == demand_vals[(branch, spec)])

    # Supply constraints: total assigned for each type <= available
    for i in range(1, 7):
        expr = gp.LinExpr()
        for (branch, spec) in allowed_by_type[i]:
            key = f"x_{i}_{branch}_{spec}"
            expr += vars_by_key[key]
        model.addConstr(expr <= available[i])

    # P2: number assigned to preferred specialty
    preferred_specialty = {
        1: 1,
        2: 2,
        3: 1,
        4: 3,
        5: 3,
        6: 3
    }

    P2_expr = gp.LinExpr()
    # Sum for each type i over branches where the specialty equals its preferred specialty
    # For each type i, include all (branch,spec) combinations where spec == preferred_specialty[i]
    for i in range(1, 7):
        pref = preferred_specialty[i]
        for (branch, spec) in allowed_by_type[i]:
            if spec == pref:
                key = f"x_{i}_{branch}_{spec}"
                P2_expr += vars_by_key[key]

    # P3: number assigned to preferred city
    preferred_city = {
        1: "Donghai",
        2: "Donghai",
        3: "Nanjiang",
        4: "Nanjiang",
        5: "Donghai",
        6: "Nanjiang"
    }

    P3_expr = gp.LinExpr()
    for i in range(1, 7):
        city = preferred_city[i]
        for (branch, spec) in allowed_by_type[i]:
            if branch == city:
                key = f"x_{i}_{branch}_{spec}"
                P3_expr += vars_by_key[key]

    # Objective: Lexicographic - implement as a weighted sum to emulate lexicographic priorities
    # High weight on P2 to dominate, then P3, plus a penalty term to guide toward P3 target
    model.setObjective(1000000.0 * P2_expr + P3_expr - 100000.0 * p3_shortfall, GRB.MAXIMIZE)

    # Expose all variables in a single dict matching required keys
    # Build the exact variables dictionary as specified
    variables = {"variables_keys": {}, "note": "Use flat variables x_Type_Branch_Specialty for assigned personnel and p3_shortfall for unmet P3 preferred-city count."}
    keys_order = [
        "x_1_Donghai_1","x_1_Donghai_2","x_1_Nanjiang_1","x_1_Nanjiang_2",
        "x_2_Donghai_2","x_2_Donghai_3","x_2_Nanjiang_2","x_2_Nanjiang_3",
        "x_3_Donghai_1","x_3_Donghai_3","x_3_Nanjiang_1","x_3_Nanjiang_3",
        "x_4_Donghai_1","x_4_Donghai_3","x_4_Nanjiang_1","x_4_Nanjiang_3",
        "x_5_Donghai_2","x_5_Donghai_3","x_5_Nanjiang_2","x_5_Nanjiang_3",
        "x_6_Donghai_3","x_6_Nanjiang_3","p3_shortfall"
    ]
    for k in keys_order:
        if k == "p3_shortfall":
            variables["variables_keys"][k] = p3_shortfall
        else:
            variables["variables_keys"][k] = vars_by_key[k]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    # Read status and objective
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.FEASIBLE: "FEASIBLE",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    st = model.Status
    status_str = status_map.get(st, "UNKNOWN")

    obj_val = float(model.ObjVal)

    # Build solution with all variable values
    # Ensure model is updated before reading X
    model.update()

    # Extract values from the variables dictionary
    sol = {}
    keys_order = [
        "x_1_Donghai_1","x_1_Donghai_2","x_1_Nanjiang_1","x_1_Nanjiang_2",
        "x_2_Donghai_2","x_2_Donghai_3","x_2_Nanjiang_2","x_2_Nanjiang_3",
        "x_3_Donghai_1","x_3_Donghai_3","x_3_Nanjiang_1","x_3_Nanjiang_3",
        "x_4_Donghai_1","x_4_Donghai_3","x_4_Nanjiang_1","x_4_Nanjiang_3",
        "x_5_Donghai_2","x_5_Donghai_3","x_5_Nanjiang_2","x_5_Nanjiang_3",
        "x_6_Donghai_3","x_6_Nanjiang_3","p3_shortfall"
    ]
    for k in keys_order:
        if k == "p3_shortfall":
            val = variables["variables_keys"][k].X
        else:
            var = variables["variables_keys"][k]
            val = var.X
        # Cast small integers to int when appropriate
        if isinstance(val, float) and abs(val - round(val)) < 1e-6:
            val = int(round(val))
        sol[k] = val

    solution = {
        "type": "object",
        "required": [
            "x_1_Donghai_1",
            "x_1_Donghai_2",
            "x_1_Nanjiang_1",
            "x_1_Nanjiang_2",
            "x_2_Donghai_2",
            "x_2_Donghai_3",
            "x_2_Nanjiang_2",
            "x_2_Nanjiang_3",
            "x_3_Donghai_1",
            "x_3_Donghai_3",
            "x_3_Nanjiang_1",
            "x_3_Nanjiang_3",
            "x_4_Donghai_1",
            "x_4_Donghai_3",
            "x_4_Nanjiang_1",
            "x_4_Nanjiang_3",
            "x_5_Donghai_2",
            "x_5_Donghai_3",
            "x_5_Nanjiang_2",
            "x_5_Nanjiang_3",
            "x_6_Donghai_3",
            "x_6_Nanjiang_3",
            "p3_shortfall"
        ],
        "properties": {},  # Filled in by the consumer if needed
    }

    # Build the exact solution dict as required by the schema
    final_solution = {k: sol[k] for k in keys_order}
    return {
        "status": status_str,
        "objective": obj_val,
        "solution": final_solution
    }