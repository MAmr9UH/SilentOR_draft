import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Initialize model
    m = gp.Model("system_reliability")

    # Read problem data
    rel = data["reliability"]
    R1 = rel["1"]  # list of length 6
    R2 = rel["2"]  # list of length 6
    R3 = rel["3"]  # list of length 6

    budget = data["budget"]
    weight_limit = data["weight_limit"]

    # Decision variables: w_a_b_c for a,b,c in {0..5}
    # 216 binary variables, keys are exactly w_{a}_{b}_{c}
    variables = {}
    for a in range(6):
        for b in range(6):
            for c in range(6):
                key = f"w_{a}_{b}_{c}"
                variables[key] = m.addVar(vtype=GRB.BINARY, name=key)

    m.update()

    # Constraint: Exactly one combination selected
    one_comb = gp.quicksum(variables[f"w_{a}_{b}_{c}"] for a in range(6) for b in range(6) for c in range(6))
    m.addConstr(one_comb == 1, name="one_combination")

    # Constraint: Budget
    budget_expr = gp.quicksum((20 * a + 30 * b + 40 * c) * variables[f"w_{a}_{b}_{c}"]
                              for a in range(6) for b in range(6) for c in range(6))
    m.addConstr(budget_expr <= budget, name="budget")

    # Constraint: Weight
    weight_expr = gp.quicksum((2 * a + 4 * b + 6 * c) * variables[f"w_{a}_{b}_{c}"]
                              for a in range(6) for b in range(6) for c in range(6))
    m.addConstr(weight_expr <= weight_limit, name="weight")

    # Objective: Maximize system reliability (product of component reliabilities)
    # Since exactly one combination is selected, maximize sum of R1[a]*R2[b]*R3[c] * w_a_b_c
    objective = gp.quicksum(
        (R1[a] * R2[b] * R3[c]) * variables[f"w_{a}_{b}_{c}"]
        for a in range(6) for b in range(6) for c in range(6)
    )
    m.setObjective(objective, GRB.MAXIMIZE)

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Read all variable values
    solution = {key: float(variables[key].X) for key in sorted(variables.keys())}

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }