def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model()

    levels = data["spare_levels"]

    # Create binary decision variables for each (a,b,c)
    w_vars = {}
    for a in levels:
        for b in levels:
            for c in levels:
                name = f"w_{a}_{b}_{c}"
                w_vars[name] = model.addVar(vtype=GRB.BINARY, name=name)

    model.update()

    # Reliability data
    r1 = data["reliability"]["1"]
    r2 = data["reliability"]["2"]
    r3 = data["reliability"]["3"]

    # Objective: maximize product of reliabilities, i.e., sum w[a,b,c] * (r1[a]*r2[b]*r3[c])
    obj_expr = None
    for a in levels:
        ra = r1[a]
        for b in levels:
            rb = r2[b]
            rb_rc = rb  # placeholder to avoid linting issues
            for c in levels:
                rc = r3[c]
                val = ra * rb * rc
                term = w_vars[f"w_{a}_{b}_{c}"] * val
                obj_expr = term if obj_expr is None else obj_expr + term

    model.setObjective(obj_expr, GRB.MAXIMIZE)

    # Exactly one combination selected
    model.addConstr(gp.quicksum(w_vars[f"w_{a}_{b}_{c}"] for a in levels for b in levels for c in levels) == 1, name="one_solution")

    # Budget constraint
    price1 = data["unit_price"]["1"]
    price2 = data["unit_price"]["2"]
    price3 = data["unit_price"]["3"]
    budget = data["budget"]

    cost_expr = gp.quicksum(w_vars[f"w_{a}_{b}_{c}"] * (price1 * a + price2 * b + price3 * c)
                            for a in levels for b in levels for c in levels)
    model.addConstr(cost_expr <= budget, name="budget")

    # Weight constraint
    weight_limit = data["weight_limit"]

    weight_expr = gp.quicksum(w_vars[f"w_{a}_{b}_{c}"] * (2 * a + 4 * b + 6 * c)
                            for a in levels for b in levels for c in levels)
    model.addConstr(weight_expr <= weight_limit, name="weight")

    return model, w_vars

def solve(data: dict) -> dict:
    from gurobipy import GRB
    model, vars = build_model(data)
    model.optimize()

    # Status string
    status_code = model.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }.get(status_code, str(status_code))

    # Objective value
    objective = float(model.ObjVal)

    # Solution values for all w variables
    model.update()
    solution = {}
    levels = data["spare_levels"]
    for a in levels:
        for b in levels:
            for c in levels:
                key = f"w_{a}_{b}_{c}"
                solution[key] = float(vars[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }