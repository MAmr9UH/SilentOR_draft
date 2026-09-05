import math
import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # number of spare levels
    spare_levels = data.get("spare_levels", [])
    n = len(spare_levels)

    # decision variables: w_a_b_c for all a,b,c in 0..n-1
    w_vars = {}
    for a in range(n):
        for b in range(n):
            for c in range(n):
                key = f"w_{a}_{b}_{c}"
                w = model.addVar(vtype=GRB.BINARY, name=key)
                w_vars[(a, b, c)] = w

    # reliabilities and logs for objective
    rel1 = data["reliability"]["1"]
    rel2 = data["reliability"]["2"]
    rel3 = data["reliability"]["3"]

    log1 = [math.log(v) for v in rel1]
    log2 = [math.log(v) for v in rel2]
    log3 = [math.log(v) for v in rel3]

    # Prices and weights per component
    p1 = data["unit_price"]["1"]
    p2 = data["unit_price"]["2"]
    p3 = data["unit_price"]["3"]

    wt1 = data["unit_weight"]["1"]
    wt2 = data["unit_weight"]["2"]
    wt3 = data["unit_weight"]["3"]

    # Objective: maximize log(product reliabilities) = sum w[a,b,c] * (log1[a] + log2[b] + log3[c])
    objective = gp.quicksum(
        w_vars[(a, b, c)] * (log1[a] + log2[b] + log3[c])
        for a in range(n) for b in range(n) for c in range(n)
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    # Constraints
    budget = data["budget"]
    weight_limit = data["weight_limit"]

    # Exactly one combination selected
    model.addConstr(
        gp.quicksum(w_vars[(a, b, c)] for a in range(n) for b in range(n) for c in range(n)) == 1,
        name="one_combination"
    )

    # Budget constraint: sum w[a,b,c] * (a*p1 + b*p2 + c*p3) <= budget
    model.addConstr(
        gp.quicksum(
            w_vars[(a, b, c)] * (a * p1 + b * p2 + c * p3)
            for a in range(n) for b in range(n) for c in range(n)
        ) <= budget,
        name="budget_constraint"
    )

    # Weight constraint: sum w[a,b,c] * (a*wt1 + b*wt2 + c*wt3) <= weight_limit
    model.addConstr(
        gp.quicksum(
            w_vars[(a, b, c)] * (a * wt1 + b * wt2 + c * wt3)
            for a in range(n) for b in range(n) for c in range(n)
        ) <= weight_limit,
        name="weight_constraint"
    )

    # Return model and a flat dict of variables with the exact keys
    variables = {}
    for a in range(n):
        for b in range(n):
            for c in range(n):
                key = f"w_{a}_{b}_{c}"
                variables[key] = w_vars[(a, b, c)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.update()
    model.optimize()

    # status string mapping
    def status_to_string(code: int) -> str:
        if code == GRB.OPTIMAL:
            return "OPTIMAL"
        if code == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if code == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if code == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if code == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        return str(code)

    status_str = status_to_string(model.Status)
    objective_value = float(model.ObjVal)

    # Read all variable values
    solution = {}
    for key in sorted(variables.keys()):
        var = variables[key]
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }