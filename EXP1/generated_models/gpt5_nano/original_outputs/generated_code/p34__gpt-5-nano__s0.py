from gurobipy import Model, GRB

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model and a dictionary of decision variables.
    The variables dictionary must contain exactly the keys:
    {"trucks_A": Var, "trucks_B": Var}
    """
    model = Model()

    # Read data with sensible fallbacks to support generic instances
    requirements = data.get("requirements", {})
    req_A = requirements.get("A", 240)
    req_B = requirements.get("B", 80)
    req_C = requirements.get("C", 120)

    freight_cost = data.get("freight_cost", {})
    cost_A = freight_cost.get("A", 200)
    cost_B = freight_cost.get("B", 160)

    truck_contents = data.get("truck_contents", {})
    contents_A = truck_contents.get("A", {})
    contents_B = truck_contents.get("B", {})

    aA = contents_A.get("A", 4)
    aB = contents_A.get("B", 2)
    aC = contents_A.get("C", 6)

    bA = contents_B.get("A", 7)
    bB = contents_B.get("B", 2)
    bC = contents_B.get("C", 2)

    # Decision variables: integer number of trucks from A and B, non-negative
    x = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    y = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    model.update()

    # Constraints: meet daily material requirements
    model.addConstr(aA * x + bA * y >= req_A, name="A_requirement")
    model.addConstr(aB * x + bB * y >= req_B, name="B_requirement")
    model.addConstr(aC * x + bC * y >= req_C, name="C_requirement")

    # Objective: minimize total freight cost
    model.setObjective(cost_A * x + cost_B * y, GRB.MINIMIZE)

    variables = {
        "trucks_A": x,
        "trucks_B": y
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map numeric status to a readable label when possible
    status_num = model.Status
    status_map = {}
    for name in dir(GRB):
        if name.isupper():
            val = getattr(GRB, name)
            if isinstance(val, int):
                status_map[val] = name
    status_str = status_map.get(status_num, str(status_num))

    obj_val = model.ObjVal
    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": {
            "trucks_A": int(variables["trucks_A"].X),
            "trucks_B": int(variables["trucks_B"].X)
        }
    }