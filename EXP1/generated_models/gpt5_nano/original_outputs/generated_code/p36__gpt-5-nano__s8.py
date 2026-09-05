import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    # Data extraction
    months = list(data.get("months", []))
    demand_raw = data.get("demand_100sqm", {})
    demand_by_m = {int(k): int(v) for k, v in demand_raw.items()}
    feasible_pairs = [(int(a), int(b)) for a, b in data.get("feasible_start_length_pairs", [])]
    contract_lengths = [int(l) for l in data.get("contract_lengths", [])]
    fees_by_length = {int(k): int(v) for k, v in data.get("fee_per_100sqm_by_length", {}).items()}
    min_distinct = int(data.get("min_distinct_lengths", 0))
    max_distinct = int(data.get("max_distinct_lengths", 0))
    mutually_exclusive = data.get("mutually_exclusive_lengths", [])

    # Variables: x_{s}_{l} for each feasible pair, and y_{l} for each length
    variables = {}

    # Build mapping from length to available start months
    by_len = {l: [] for l in contract_lengths}
    for s, l in feasible_pairs:
        key = f"x_{s}_{l}"
        var = m.addVar(vtype=GRB.INTEGER, lb=0, name=key)
        variables[key] = var
        by_len.setdefault(l, []).append(s)

    for l in contract_lengths:
        key = f"y_{l}"
        var = m.addVar(vtype=GRB.BINARY, lb=0, name=key)
        variables[key] = var

    m.update()

    # Demand constraints: for each month m, sum of covering contracts equals demand
    for mth in months:
        covering = gp.quicksum(variables[f"x_{s}_{l}"] for (s, l) in feasible_pairs if s <= mth <= s + l - 1)
        m.addConstr(covering == demand_by_m.get(mth, 0), name=f"demand_m{mth}")

    # Distinct lengths constraints
    total_lengths_used = gp.quicksum(variables[f"y_{l}"] for l in contract_lengths)
    m.addConstr(total_lengths_used >= min_distinct, name="min_distinct_lengths")
    m.addConstr(total_lengths_used <= max_distinct, name="max_distinct_lengths")
    m.addConstr(total_lengths_used <= 3, name="max_three_lengths")

    # Mutually exclusive lengths
    # e.g., lengths 1 and 4 cannot both be used
    if 1 in contract_lengths and 4 in contract_lengths:
        m.addConstr(variables["y_1"] + variables["y_4"] <= 1, name="mutual_1_4")

    # Link x and y: sum_x_l <= BIG * y_l and sum_x_l >= y_l
    total_demand = sum(demand_by_m.get(m, 0) for m in months)
    BIG = max(1, total_demand)

    for l in contract_lengths:
        s_list = by_len.get(l, [])
        if len(s_list) == 0:
            # No contracts of this length exist; force y_l = 0
            m.addConstr(0 <= BIG * variables[f"y_{l}"], name=f"link_zero_upper_y_{l}")
            m.addConstr(variables[f"y_{l}"] <= 0, name=f"force_y_zero_{l}")
        else:
            sum_x_l = gp.quicksum(variables[f"x_{s}_{l}"] for s in s_list)
            m.addConstr(sum_x_l <= BIG * variables[f"y_{l}"], name=f"link_sum_x_to_y_upper_{l}")
            m.addConstr(sum_x_l >= variables[f"y_{l}"], name=f"link_sum_x_to_y_lower_{l}")

    # Objective: minimize total rental cost
    objective = gp.quicksum(variables[f"x_{s}_{l}"] * fees_by_length[l]
                            for (s, l) in feasible_pairs)
    m.setObjective(objective, GRB.MINIMIZE)

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
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

    objective_val = float(model.ObjVal) if model.ObjVal is not None else float('nan')

    # Compile solution vector
    keys_order = [
        "x_1_1", "x_1_2", "x_1_3", "x_1_4",
        "x_2_1", "x_2_2", "x_2_3",
        "x_3_1", "x_3_2",
        "x_4_1",
        "y_1", "y_2", "y_3", "y_4"
    ]
    solution = {}
    for k in keys_order:
        v = variables.get(k)
        if v is None:
            val = 0.0
        else:
            val = float(v.X) if v.X is not None else 0.0
        solution[k] = val

    # Build final schema
    output = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "minimum total rental cost"},
            "solution": {
                "type": "object",
                "required": keys_order,
                "properties": {k: {"type": "number"} for k in keys_order}
            }
        }
    }

    return {
        "type": status_str,  # provide status string as top-level type in this wrapper
        "objective": objective_val,
        "solution": solution
    }