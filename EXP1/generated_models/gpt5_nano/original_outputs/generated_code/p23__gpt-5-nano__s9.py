import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict):
    spare_levels = data["spare_levels"]
    price1 = data["unit_price"]["1"]
    price2 = data["unit_price"]["2"]
    price3 = data["unit_price"]["3"]
    wt1 = data["unit_weight"]["1"]
    wt2 = data["unit_weight"]["2"]
    wt3 = data["unit_weight"]["3"]
    budget = data["budget"]
    weight_limit = data["weight_limit"]

    rel1 = data["reliability"]["1"]
    rel2 = data["reliability"]["2"]
    rel3 = data["reliability"]["3"]

    # Build maps for quick access
    rel1_map = {a: rel1[idx] for idx, a in enumerate(spare_levels)}
    rel2_map = {b: rel2[idx] for idx, b in enumerate(spare_levels)}
    rel3_map = {c: rel3[idx] for idx, c in enumerate(spare_levels)}

    logrel1 = {a: math.log(rel1_map[a]) for a in spare_levels}
    logrel2 = {b: math.log(rel2_map[b]) for b in spare_levels}
    logrel3 = {c: math.log(rel3_map[c]) for c in spare_levels}

    model = gp.Model()

    # Create decision variables: w_a_b_c for all a,b,c in spare_levels
    variables = {}
    for a in spare_levels:
        for b in spare_levels:
            for c in spare_levels:
                key = f"w_{a}_{b}_{c}"
                v = model.addVar(vtype=GRB.BINARY, name=key)
                variables[key] = v

    # Exactly one combination selected
    one_combo = gp.quicksum(variables[f"w_{a}_{b}_{c}"] for a in spare_levels for b in spare_levels for c in spare_levels)
    model.addConstr(one_combo == 1, name="OneCombo")

    # Budget and weight constraints
    cost_expr = gp.quicksum(
        variables[f"w_{a}_{b}_{c}"] * (a * price1 + b * price2 + c * price3)
        for a in spare_levels for b in spare_levels for c in spare_levels
    )
    model.addConstr(cost_expr <= budget, name="Budget")

    weight_expr = gp.quicksum(
        variables[f"w_{a}_{b}_{c}"] * (a * wt1 + b * wt2 + c * wt3)
        for a in spare_levels for b in spare_levels for c in spare_levels
    )
    model.addConstr(weight_expr <= weight_limit, name="Weight")

    # Objective: maximize product of reliabilities
    # Since exactly one combination is chosen, maximizing log(product) is equivalent.
    obj_expr = gp.quicksum(
        variables[f"w_{a}_{b}_{c}"] * (logrel1[a] + logrel2[b] + logrel3[c])
        for a in spare_levels for b in spare_levels for c in spare_levels
    )
    model.setObjective(obj_expr, GRB.MAXIMIZE)

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Status string mapping
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    # Objective value: exp of log-objective to get the actual reliability
    obj_log = model.ObjVal
    objective_value = math.exp(obj_log) if obj_log is not None else None

    # Build solution dict: values of all w_a_b_c variables
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": float(objective_value) if objective_value is not None else None,
        "solution": solution
    }