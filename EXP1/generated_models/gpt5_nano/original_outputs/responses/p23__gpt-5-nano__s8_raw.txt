import math
from gurobipy import (
    Model,
    GRB,
    quicksum
)

def build_model(data: dict):
    # Extract data
    R1 = data["reliability"]["1"]  # list of 6 reliability values for component 1
    R2 = data["reliability"]["2"]  # list of 6 reliability values for component 2
    R3 = data["reliability"]["3"]  # list of 6 reliability values for component 3

    P1 = data["unit_price"]["1"]
    P2 = data["unit_price"]["2"]
    P3 = data["unit_price"]["3"]

    W1 = data["unit_weight"]["1"]
    W2 = data["unit_weight"]["2"]
    W3 = data["unit_weight"]["3"]

    budget = data["budget"]
    weight_limit = data["weight_limit"]

    # Precompute logs for objective: maximize log(R1)* + log(R2)* + log(R3)*
    logR1 = [math.log(val) for val in R1]
    logR2 = [math.log(val) for val in R2]
    logR3 = [math.log(val) for val in R3]

    model = Model()

    # Decision variables: w_a_b_c binary for a,b,c in 0..5
    # Build flat dict of variables with exact keys
    variables = {}
    len1 = len(R1)
    len2 = len(R2)
    len3 = len(R3)

    for a in range(len1):
        for b in range(len2):
            for c in range(len3):
                key = f"w_{a}_{b}_{c}"
                v = model.addVar(vtype=GRB.BINARY, name=key)
                variables[key] = v

    model.update()

    # Exactly one combination selected
    model.addConstr(
        quicksum(variables[f"w_{a}_{b}_{c}"] for a in range(len1) for b in range(len2) for c in range(len3)) == 1,
        name="OneCombination"
    )

    # Budget constraint
    budget_expr = quicksum(
        variables[f"w_{a}_{b}_{c}"] * (a * P1 + b * P2 + c * P3)
        for a in range(len1) for b in range(len2) for c in range(len3)
    )
    model.addConstr(budget_expr <= budget, name="Budget")

    # Weight constraint
    weight_expr = quicksum(
        variables[f"w_{a}_{b}_{c}"] * (a * W1 + b * W2 + c * W3)
        for a in range(len1) for b in range(len2) for c in range(len3)
    )
    model.addConstr(weight_expr <= weight_limit, name="Weight")

    # Objective: maximize sum over w_a_b_c of logR1[a] + logR2[b] + logR3[c]
    obj_expr = quicksum(
        variables[f"w_{a}_{b}_{c}"] * (logR1[a] + logR2[b] + logR3[c])
        for a in range(len1) for b in range(len2) for c in range(len3)
    )
    model.setObjective(obj_expr, GRB.MAXIMIZE)

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Identify selected combination and compute objective value as the actual reliability product
    selected = None
    for a in range(len(data["reliability"]["1"])):
        for b in range(len(data["reliability"]["2"])):
            for c in range(len(data["reliability"]["3"])):
                key = f"w_{a}_{b}_{c}"
                val = variables[key].X
                if val is not None and val > 0.5:
                    selected = (a, b, c)
                    break
            if selected is not None:
                break
        if selected is not None:
            break

    if selected is None:
        # No feasible solution found; set objective to 0
        objective_value = 0.0
    else:
        a, b, c = selected
        R1 = data["reliability"]["1"]
        R2 = data["reliability"]["2"]
        R3 = data["reliability"]["3"]
        objective_value = float(R1[a] * R2[b] * R3[c])

    # Build solution dict with all w_a_b_c keys
    solution = {}
    len1 = len(data["reliability"]["1"])
    len2 = len(data["reliability"]["2"])
    len3 = len(data["reliability"]["3"])
    for a in range(len1):
        for b in range(len2):
            for c in range(len3):
                key = f"w_{a}_{b}_{c}"
                v = variables[key].X
                solution[key] = float(v)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }