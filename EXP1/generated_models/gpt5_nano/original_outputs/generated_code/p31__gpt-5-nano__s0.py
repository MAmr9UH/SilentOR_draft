import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    branches = data["branches"]  # ["Donghai","Nanjiang"]
    types = [str(t) for t in data["types"]]  # ["1","2","3","4","5","6"]

    # Build support structures
    available_people = {str(t): data["available_people"][str(t)] for t in data["types"]}
    suitable = {str(t): [int(x) for x in data["suitable_specialties"][str(t)]] for t in data["types"]}
    preferred_specialty = {str(t): int(data["preferred_specialty"][str(t)]) for t in data["types"]}
    preferred_city = {str(t): data["preferred_city"][str(t)] for t in data["types"]}

    # Decision variables: x_t_b_s for each feasible (t, branch, s)
    x_vars = {}
    for t in data["types"]:
        tkey = str(t)
        for b in branches:
            for s in suitable[tkey]:
                key = (tkey, b, s)
                var = model.addVar(lb=0, ub=GRB.INFINITY, vtype=GRB.INTEGER, name=f"x_{tkey}_{b}_{s}")
                x_vars[key] = var

    # p3_shortfall variable
    p3_shortfall = model.addVar(lb=0, vtype=GRB.INTEGER, name="p3_shortfall")

    model.update()

    # P1: meet all specialty demands at both branches (equalities)
    for br in branches:
        for s in data["specialties"]:
            D = data["demand"][f"{br}_{s}"]
            expr = gp.quicksum(x_vars[(tkey, br, s)]
                               for tkey in types
                               if s in suitable[tkey])
            model.addConstr(expr == D, name=f"Demand_{br}_{s}")

    # P2 and P3: objective will be a single lexicographic composition via large-weighting
    # P2: number assigned to preferred specialty
    P2_expr = gp.quicksum(
        x_vars[(tkey, b, s)]
        for tkey in types
        for b in branches
        for s in suitable[tkey]
        if s == preferred_specialty[tkey]
    )

    # P3: number assigned to preferred city
    P3_expr = gp.quicksum(
        x_vars[(tkey, preferred_city[tkey], s)]
        for tkey in types
        for s in suitable[tkey]
    )

    # p3_shortfall constraint: p3_shortfall >= 8000 - P3_expr
    model.addConstr(p3_shortfall >= 8000 - P3_expr, name="P3_shortfall_bound")

    # Supply constraints: sum of all allocations for a type <= availability
    for tkey in types:
        expr = gp.quicksum(x_vars[(tkey, br, s)]
                           for br in branches
                           for s in suitable[tkey])
        model.addConstr(expr <= available_people[tkey], name=f"Supply_{tkey}")

    # Objective: lexicographic by using a large-weight single objective
    # Let M be a large base; we use Z = P2*(M^2) + P3*(M) - p3_shortfall
    M = 1000
    Z = P2_expr * (M**2) + P3_expr * M - p3_shortfall
    model.setObjective(Z, GRB.MAXIMIZE)

    # Expose variables dictionary as required by the caller
    variables_keys = {}
    for tkey in types:
        for b in branches:
            for s in suitable[tkey]:
                key = f"x_{tkey}_{b}_{s}"
                variables_keys[key] = x_vars[(tkey, b, s)]
    variables_keys["p3_shortfall"] = p3_shortfall

    # Return the model and the mapping as required
    return model, {"variables_keys": variables_keys, "note": "Use flat variables x_Type_Branch_Specialty for assigned personnel and p3_shortfall for unmet P3 preferred-city count."}


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.update()
    model.optimize()

    # Prepare status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }
    status = status_map.get(model.Status, str(model.Status))

    # Read values
    var_map = variables.get("variables_keys", {})
    # Expected keys in solution
    required_keys = [
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
    ]

    solution = {}
    # Populate solution values
    for key in required_keys:
        if key in var_map:
            solution[key] = int(var_map[key].X)
        else:
            # Defensive: if a key is missing (shouldn't happen), set to 0
            solution[key] = 0

    # Objective report: minimum P3 shortfall (the actual shortfall at optimum)
    objective_value = int(solution["p3_shortfall"])

    return {
        "status": status,
        "objective": objective_value,
        "solution": solution
    }