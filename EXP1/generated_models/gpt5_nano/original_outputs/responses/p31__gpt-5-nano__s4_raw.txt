import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Normalize data
    branches = ["Donghai", "Nanjiang"]
    types = data["types"]  # [1..6]
    available = {str(t): int(data["available_people"][str(t)]) for t in types}
    suitable = {str(t): list(map(int, data["suitable_specialties"][str(t)])) for t in types}
    pref_spec = {str(t): int(data["preferred_specialty"][str(t)]) for t in types}
    pref_city = {str(t): data["preferred_city"][str(t)] for t in types}
    demand = data["demand"]  # keys like "Donghai_1" etc

    # Create decision variables
    # x_{type}_{branch}_{specialty}
    var_map = {}  # (t, branch, s) -> var
    variables = {}

    for t in types:
        t_str = str(t)
        for branch in branches:
            for s in data["specialties"]:
                if s in suitable[t_str]:
                    name = f"x_{t}_{branch}_{s}"
                    v = model.addVar(lb=0, ub=available[t_str], vtype=GRB.INTEGER, name=name)
                    var_map[(t, branch, s)] = v
                    variables[name] = v  # keys mirror required naming
    # p3_shortfall variable
    p3_shortfall = model.addVar(lb=0, vtype=GRB.INTEGER, name="p3_shortfall")
    variables["p3_shortfall"] = p3_shortfall

    model.update()

    # Demand constraints (P1: fully meet specialty demands)
    for br in branches:
        for s in data["specialties"]:
            key = f"{br}_{s}"
            if key in demand:
                D = int(demand[key])
                expr = quicksum(var_map[(t, br, s)]
                                for t in types
                                if (t, br, s) in var_map)
                model.addConstr(expr == D, name=f"Demand_{br}_{s}")

    # Supply constraints: total assigned from each type cannot exceed available
    for t in types:
        t_str = str(t)
        expr = quicksum(var_map[(t, br, s)]
                        for br in branches
                        for s in suitable[t_str]
                        if (t, br, s) in var_map)
        model.addConstr(expr <= available[t_str], name=f"Supply_T{t}")

    # P2: preferred specialty assignments
    P2_expr = None
    P2_expr = gp.LinExpr()
    for t in types:
        t_str = str(t)
        pref_s = pref_spec[t_str]
        for br in branches:
            if (t, br, pref_s) in var_map:
                P2_expr += var_map[(t, br, pref_s)]

    # P3: preferred city assignments
    P3_expr = gp.LinExpr()
    for t in types:
        t_str = str(t)
        city = pref_city[t_str]
        for br in branches:
            if br == city and (t, br, pref_s) in var_map:
                # Note: pref_s variable name may not exist; ensure we add all with city match
                # Iterate over all specialties valid for this type and add those in the preferred city
                for s in suitable[t_str]:
                    if (t, br, s) in var_map:
                        P3_expr += var_map[(t, br, s)]
            else:
                # If preferred city matches but there is no such (t, br, s) variable for other s, skip
                continue

    # p3_shortfall constraints: p3_shortfall >= 8000 - P3_expr
    target_P3 = int(data["p3_preferred_city_target"])
    model.addConstr(p3_shortfall >= target_P3 - P3_expr, name="P3_Shortfall_lowerbound")

    # Objective: lexicographic via a single goal with big-M trick
    # Maximize O = M * P2_expr - p3_shortfall
    M = 100000  # large enough to dominate p3_shortfall (max ~8000)
    Objective = M * P2_expr - p3_shortfall
    model.setObjective(Objective, GRB.MAXIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    # Read objective result: minimum P3 shortfall
    p3_shortfall_val = None
    if "p3_shortfall" in variables:
        p3_shortfall_val = int(variables["p3_shortfall"].X + 0.0)  # ensure int

    # Solution dictionary with all required x variables and p3_shortfall
    solution = {}
    keys_order = [
        "x_1_Donghai_1","x_1_Donghai_2","x_1_Nanjiang_1","x_1_Nanjiang_2",
        "x_2_Donghai_2","x_2_Donghai_3","x_2_Nanjiang_2","x_2_Nanjiang_3",
        "x_3_Donghai_1","x_3_Donghai_3","x_3_Nanjiang_1","x_3_Nanjiang_3",
        "x_4_Donghai_1","x_4_Donghai_3","x_4_Nanjiang_1","x_4_Nanjiang_3",
        "x_5_Donghai_2","x_5_Donghai_3","x_5_Nanjiang_2","x_5_Nanjiang_3",
        "x_6_Donghai_3","x_6_Nanjiang_3","p3_shortfall"
    ]
    for key in keys_order:
        if key == "p3_shortfall":
            solution[key] = int(variables.get("p3_shortfall").X + 0.0) if "p3_shortfall" in variables else 0
        else:
            if key in variables:
                solution[key] = int(variables[key].X + 0.0)
            else:
                solution[key] = 0

    objective_value = None
    if "p3_shortfall" in variables:
        objective_value = int(variables["p3_shortfall"].X + 0.0)

    return {
        "type": "object",
        "status": status,
        "objective": objective_value,
        "solution": solution
    }