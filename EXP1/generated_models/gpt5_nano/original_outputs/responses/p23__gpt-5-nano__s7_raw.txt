import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model and a mapping of all decision variables.
    The decision variables are the complete spare-count combinations w_a_b_c.
    """
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    spare_levels = data.get("spare_levels", [])
    nA = len(spare_levels)
    nB = len(spare_levels)
    nC = len(spare_levels)

    price1 = data["unit_price"]["1"]
    price2 = data["unit_price"]["2"]
    price3 = data["unit_price"]["3"]

    wt1 = data["unit_weight"]["1"]
    wt2 = data["unit_weight"]["2"]
    wt3 = data["unit_weight"]["3"]

    budget = data["budget"]
    weight_limit = data["weight_limit"]

    # Reliability values
    r1 = data["reliability"]["1"]
    r2 = data["reliability"]["2"]
    r3 = data["reliability"]["3"]

    # Create all binary decision variables w_{a}_{b}_{c}
    variables = {}
    for a in range(nA):
        for b in range(nB):
            for c in range(nC):
                key = f"w_{a}_{b}_{c}"
                variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    model.update()  # ensure variables are registered before constraints

    # Constraint: Exactly one combination selected
    model.addConstr(gp.quicksum(variables[f"w_{a}_{b}_{c}"] for a in range(nA) for b in range(nB) for c in range(nC)) == 1, name="OneCombo")

    # Constraint: Budget
    budget_expr = gp.quicksum(
        (a * price1 + b * price2 + c * price3) * variables[f"w_{a}_{b}_{c}"]
        for a in range(nA) for b in range(nB) for c in range(nC)
    )
    model.addConstr(budget_expr <= budget, name="Budget")

    # Constraint: Weight
    weight_expr = gp.quicksum(
        (a * wt1 + b * wt2 + c * wt3) * variables[f"w_{a}_{b}_{c}"]
        for a in range(nA) for b in range(nB) for c in range(nC)
    )
    model.addConstr(weight_expr <= weight_limit, name="Weight")

    # Objective: maximize system reliability = sum w_{a,b,c} * (r1[a] * r2[b] * r3[c])
    obj_expr = gp.quicksum(
        (r1[a] * r2[b] * r3[c]) * variables[f"w_{a}_{b}_{c}"]
        for a in range(nA) for b in range(nB) for c in range(nC)
    )
    model.setObjective(obj_expr, gp.GRB.MAXIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the solution in the required schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = int(model.Status)
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.CUTOFF: "CUTOFF",
    }
    status_str = status_map.get(status_code, f"STATUS_{status_code}")

    # Build solution dictionary with all w_a_b_c values
    model.update()
    solution = {}
    spare_levels = data.get("spare_levels", [])
    nA = len(spare_levels)
    nB = len(spare_levels)
    nC = len(spare_levels)
    for a in range(nA):
        for b in range(nB):
            for c in range(nC):
                key = f"w_{a}_{b}_{c}"
                solution[key] = float(variables[key].X)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }