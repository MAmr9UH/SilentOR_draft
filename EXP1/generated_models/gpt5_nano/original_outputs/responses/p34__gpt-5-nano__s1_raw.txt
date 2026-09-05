def build_model(data: dict) -> tuple:
    import gurobipy as gp

    model = gp.Model()

    # Demands (with safe defaults if not provided in data)
    req = data.get("requirements", {})
    A_need = req.get("A", 240)
    B_need = req.get("B", 80)
    C_need = req.get("C", 120)

    # Truck contents from data (defaults to problem's values if not provided)
    truck_contents = data.get("truck_contents", {})
    contents_A = truck_contents.get("A", {"A": 4, "B": 2, "C": 6})
    contents_B = truck_contents.get("B", {"A": 7, "B": 2, "C": 2})

    A_A = contents_A.get("A", 0)  # A transported by a truck from A
    A_B = contents_B.get("A", 0)  # A transported by a truck from B

    B_A = contents_A.get("B", 0)  # B transported by a truck from A
    B_B = contents_B.get("B", 0)  # B transported by a truck from B

    C_A = contents_A.get("C", 0)  # C transported by a truck from A
    C_B = contents_B.get("C", 0)  # C transported by a truck from B

    # Freight costs
    freight = data.get("freight_cost", {})
    cost_A = freight.get("A", 0)
    cost_B = freight.get("B", 0)

    # Decision variables (integers, >= 0)
    trucks_A = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="trucks_B")

    # Constraints: meet all material demands
    model.addConstr(A_A * trucks_A + A_B * trucks_B >= A_need, name="A_need")
    model.addConstr(B_A * trucks_A + B_B * trucks_B >= B_need, name="B_need")
    model.addConstr(C_A * trucks_A + C_B * trucks_B >= C_need, name="C_need")

    # Objective: minimize total freight cost
    model.setObjective(cost_A * trucks_A + cost_B * trucks_B, gp.GRB.MINIMIZE)

    model.update()

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    return model, variables

def solve(data: dict) -> dict:
    import gurobipy as gp

    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_int = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
        gp.GRB.INTERRUPTED: "INTERRUPTED"
    }
    status_str = status_map.get(status_int, str(status_int))

    # Objective value (when optimal, otherwise best available)
    objective_value = None
    try:
        if hasattr(model, "ObjVal"):
            objective_value = float(model.ObjVal)
    except Exception:
        objective_value = None
    if objective_value is None:
        objective_value = 0.0

    solution = {
        "trucks_A": int(variables["trucks_A"].X),
        "trucks_B": int(variables["trucks_B"].X)
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }