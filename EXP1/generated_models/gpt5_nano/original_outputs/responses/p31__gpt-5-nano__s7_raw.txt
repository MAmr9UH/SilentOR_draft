import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Initialize model
    model = gp.Model("Lexico_Goals_Recruitment")
    model.setParam('OutputFlag', 0)

    branches = data["branches"]
    specialties = data["specialties"]
    types = data["types"]

    available_people = {str(k): int(v) for k, v in data["available_people"].items()}
    suitable_specialties = {str(k): list(v) for k, v in data["suitable_specialties"].items()}
    preferred_specialty = {str(k): int(v) for k, v in data["preferred_specialty"].items()}
    preferred_city = {str(k): data["preferred_city"][str(k)] for k in data["types"]}

    demand = data["demand"]

    # Create decision variables x_i_branch_s for all feasible (type i, branch, specialty)
    variables = {}
    for i in types:
        i_str = str(i)
        for branch in branches:
            for s in suitable_specialties[i_str]:
                key = f"x_{i}_{branch}_{s}"
                v = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
                variables[key] = v

    # p3_shortfall variable (integer, nonnegative)
    p3_shortfall = model.addVar(vtype=GRB.INTEGER, lb=0, name="p3_shortfall")

    model.update()

    # Demand constraints: for each (branch, specialty), sum of assigned >= demand
    for branch in branches:
        for s in specialties:
            demand_key = f"{branch}_{s}"
            d = int(demand[demand_key])
            expr = gp.quicksum(
                variables[f"x_{i}_{branch}_{s}"]
                for i in types
                if str(s) in suitable_specialities := suitable_specialities[str(i)]
            )
            # The above expression uses a Python assignment expression to ensure compatibility;
            # However to stay safe, rebuild without walrus operator:
    # Rebuild demand constraints without walrus operator
    for branch in branches:
        for s in specialties:
            d = int(demand[f"{branch}_{s}"])
            expr = gp.quicksum(
                variables[f"x_{i}_{branch}_{s}"]
                for i in types
                if s in suitable_specialties[str(i)]
                if f"x_{i}_{branch}_{s}" in variables
            )
            model.addConstr(expr >= d, name=f"Demand_{branch}_{s}")

    # Supply constraints: sum over all (branch, specialty) for each type i <= available
    for i in types:
        i_str = str(i)
        expr = gp.quicksum(
            variables[f"x_{i}_{branch}_{s}"]
            for branch in branches
            for s in suitable_specialties[i_str]
            if f"x_{i}_{branch}_{s}" in variables
        )
        model.addConstr(expr <= int(available_people[i_str]), name=f"Supply_{i}")

    # P2: number assigned to preferred specialty
    P2_expr = gp.LinExpr()
    for i in types:
        i_str = str(i)
        pref_s = preferred_specialty[i_str]
        for branch in branches:
            for s in suitable_specialties[i_str]:
                if s == pref_s and f"x_{i}_{branch}_{s}" in variables:
                    P2_expr.add(variables[f"x_{i}_{branch}_{s}"])

    # P3: number assigned to preferred city (sum over types assigned to their preferred city across both branches)
    P3_expr = gp.LinExpr()
    for i in types:
        i_str = str(i)
        city_pref = preferred_city[i_str]
        # The type is counted if assigned to its preferred city in any suitable specialty
        for s in suitable_specialties[i_str]:
            key = f"x_{i}_{city_pref}_{s}"
            if key in variables:
                P3_expr.add(variables[key])

    # Objective functions (lexicographic):
    # 1) Maximize P2 (priority highest)
    # 2) Minimize p3_shortfall (priority next) with relation to 8000 target
    # 3) Maximize P3_expr as a tie-breaker
    model.setObjectiveN(P2_expr, 0, 1, 0)            # Primary: P2
    model.setObjectiveN(p3_shortfall, 1, 2, 0)      # Secondary: minimize P3 shortfall
    model.setObjectiveN(P3_expr, 2, 3, 0)           # Tertiary: maximize P3 count

    # P3 shortfall constraint: p3_shortfall >= 8000 - P3_expr  and p3_shortfall >= 0
    model.addConstr(p3_shortfall >= 8000 - P3_expr, name="P3_Target_Slack1")
    model.update()

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    # Read status
    st = model.Status
    if st == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif st == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    else:
        status = str(st)

    # Objective value is captured via p3_shortfall (as per schema)
    # Ensure variable has value
    model.update()
    p3_shortfall_val = int(variables["p3_shortfall"].X)

    # Build solution dict with all required x variables and p3_shortfall
    solution = {}
    for key in [
        "x_1_Donghai_1","x_1_Donghai_2","x_1_Nanjiang_1","x_1_Nanjiang_2",
        "x_2_Donghai_2","x_2_Donghai_3","x_2_Nanjiang_2","x_2_Nanjiang_3",
        "x_3_Donghai_1","x_3_Donghai_3","x_3_Nanjiang_1","x_3_Nanjiang_3",
        "x_4_Donghai_1","x_4_Donghai_3","x_4_Nanjiang_1","x_4_Nanjiang_3",
        "x_5_Donghai_2","x_5_Donghai_3","x_5_Nanjiang_2","x_5_Nanjiang_3",
        "x_6_Donghai_3","x_6_Nanjiang_3",
    ]:
        v = variables[key]
        solution[key] = float(v.X)

    return {
        "type": "object",
        "status": status,
        "objective": float(p3_shortfall_val),
        "solution": solution
    }