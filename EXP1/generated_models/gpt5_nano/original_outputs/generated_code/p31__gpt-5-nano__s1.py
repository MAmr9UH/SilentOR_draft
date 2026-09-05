import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    branches = data["branches"]
    types = data["types"]
    available_people = data["available_people"]
    suitable_specialties = data["suitable_specialties"]
    preferred_specialty = data["preferred_specialty"]
    preferred_city = data["preferred_city"]
    demand = data["demand"]

    # Create variables x_type_branch_specialty and p3_shortfall
    variables = {}

    # Create x_i_b_s for each type, branch, and suitable specialty
    for t in types:
        t_str = str(t)
        ub = int(available_people[t_str])
        s_list = suitable_specialties[t_str]
        for b in branches:
            for s in s_list:
                key = f"x_{t}_{b}_{s}"
                var = model.addVar(lb=0, ub=ub, vtype=GRB.INTEGER, name=key)
                variables[key] = var

    # p3_shortfall variable
    p3_shortfall = model.addVar(lb=0, vtype=GRB.INTEGER, name="p3_shortfall")
    variables["p3_shortfall"] = p3_shortfall

    model.update()

    # P1: Fully meet all specialty demands at both branches
    for br in branches:
        for s in data["specialties"]:
            demand_key = f"{br}_{s}"
            demand_value = demand.get(demand_key, 0)
            expr = gp.quicksum(
                variables.get(f"x_{t}_{br}_{s}", 0)
                for t in types
                if s in suitable_specialities := suitable_specialties[str(t)]
            )
            model.addConstr(expr == demand_value, name=f"Dem_{demand_key}")

    # P1 is fully enforced by equality constraints as above.

    # P2 and P3 (lexicographic) will be encoded via multi-objective later
    # Define auxiliary expressions for P2 and P3
    # P2: number of recruited personnel assigned to their preferred specialty
    p2_terms = []
    for t in types:
        t_str = str(t)
        pref_s = int(preferred_specialty[t_str])
        for br in branches:
            if pref_s in suitable_specialities[t_str]:
                key = f"x_{t}_{br}_{pref_s}"
                if key in variables:
                    p2_terms.append(variables[key])
    p2_sum = gp.quicksum(p2_terms)

    # P3: number assigned to preferred city
    p3_terms = []
    for t in types:
        t_str = str(t)
        city_pref = preferred_city[t_str]
        if city_pref in branches:
            for s in suitable_specialties[t_str]:
                key = f"x_{t}_{city_pref}_{s}"
                if key in variables:
                    p3_terms.append(variables[key])
    p3_sum = gp.quicksum(p3_terms)

    # P3 shortfall constraint: p3_shortfall >= 8000 - p3_sum and >= 0
    model.addConstr(p3_shortfall >= 8000 - p3_sum, name="P3_Shortfall_Def1")
    model.addConstr(p3_shortfall >= 0, name="P3_Shortfall_Def2")

    # Multiobjective: 1) maximize P2 (i.e., minimize -P2), 2) minimize P3 shortfall
    model.setObjectiveN(-p2_sum, index=0, priority=2)
    model.setObjectiveN(p3_shortfall, index=1, priority=1)

    # Attach to return
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    # Build solution dict with all variable values
    solution = {}
    for key, var in variables.items():
        val = var.X
        # Cast to int where appropriate
        if isinstance(val, float) and abs(val - int(val)) < 1e-6:
            val = int(val)
        solution[key] = val

    # Objective value as minimum P3 shortfall
    objective_value = int(variables.get("p3_shortfall").X) if "p3_shortfall" in variables else None

    return {
        "status": status,
        "objective": objective_value,
        "solution": solution
    }