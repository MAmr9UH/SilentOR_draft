import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    rel = data["reliability"]
    rel1 = rel["1"]
    rel2 = rel["2"]
    rel3 = rel["3"]
    price1 = data["unit_price"]["1"]
    price2 = data["unit_price"]["2"]
    price3 = data["unit_price"]["3"]
    w1 = data["unit_weight"]["1"]
    w2 = data["unit_weight"]["2"]
    w3 = data["unit_weight"]["3"]
    budget = data["budget"]
    weight_limit = data["weight_limit"]
    spare_levels = data["spare_levels"]

    variables = {}
    for a in spare_levels:
        for b in spare_levels:
            for c in spare_levels:
                key = f"w_{a}_{b}_{c}"
                variables[key] = m.addVar(vtype=GRB.BINARY, name=key)

    m.update()

    one_combo = gp.quicksum(variables[f"w_{a}_{b}_{c}"] for a in spare_levels for b in spare_levels for c in spare_levels)
    m.addConstr(one_combo == 1, name="one_combo")

    cost_expr = gp.quicksum(variables[f"w_{a}_{b}_{c}"] * (a * price1 + b * price2 + c * price3)
                             for a in spare_levels for b in spare_levels for c in spare_levels)
    m.addConstr(cost_expr <= budget, name="budget")

    wt_expr = gp.quicksum(variables[f"w_{a}_{b}_{c}"] * (a * w1 + b * w2 + c * w3)
                             for a in spare_levels for b in spare_levels for c in spare_levels)
    m.addConstr(wt_expr <= weight_limit, name="weight")

    p_expr = gp.quicksum(variables[f"w_{a}_{b}_{c}"] * (rel1[a] * rel2[b] * rel3[c])
                         for a in spare_levels for b in spare_levels for c in spare_levels)
    R = m.addVar(vtype=GRB.CONTINUOUS, name="R")
    m.addConstr(R <= p_expr, name="R_bound")

    m.setObjective(R, GRB.MAXIMIZE)
    m.update()
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
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

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    spare_levels = data["spare_levels"]
    for a in spare_levels:
        for b in spare_levels:
            for c in spare_levels:
                key = f"w_{a}_{b}_{c}"
                solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }