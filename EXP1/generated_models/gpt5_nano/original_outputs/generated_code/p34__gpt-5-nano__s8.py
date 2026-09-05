from gurobipy import Model, GRB

def build_model(data: dict) -> tuple:
    """
    Build and configure the Gurobi model for the daily truck dispatch problem.

    Returns:
        model: The constructed Gurobi Model (not optimized).
        variables: A dict with keys "trucks_A" and "trucks_B" mapping to the corresponding Var objects.
    """
    model = Model()
    model.Params.OutputFlag = 0  # silence solver output

    # Decision variables: number of trucks from each warehouse
    trucks_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    model.update()

    # Extract data
    truck_A_contents = data["truck_contents"]["A"]
    truck_B_contents = data["truck_contents"]["B"]

    # Required minimums (allow override via data["requirements"] if provided)
    req_A = data.get("requirements", {}).get("A", 240)
    req_B = data.get("requirements", {}).get("B", 80)
    req_C = data.get("requirements", {}).get("C", 120)

    raw_materials = data["raw_materials"]

    # Constraints: meet minimums for A, B, C
    # For each material, compute total from both warehouses and constrain >= required
    required_map = {"A": req_A, "B": req_B, "C": req_C}
    for rm in raw_materials:
        amount_from_A = truck_A_contents.get(rm, 0)
        amount_from_B = truck_B_contents.get(rm, 0)
        required = required_map.get(rm, 0)

        model.addConstr(amount_from_A * trucks_A + amount_from_B * trucks_B >= required,
                        name=f"cons_{rm}")

    # Objective: minimize total freight cost
    cost_A = data["freight_cost"]["A"]
    cost_B = data["freight_cost"]["B"]
    model.setObjective(cost_A * trucks_A + cost_B * trucks_B, GRB.MINIMIZE)

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    return model, variables


def solve(data: dict) -> dict:
    """
    Solve the optimization problem and return the results in the required schema.

    The returned dict follows a schema with keys: status, objective, solution(trucks_A, trucks_B).
    """
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
    status_val = model.Status
    status_str = status_map.get(status_val, str(status_val))

    # Read objective value and solution
    objective = float(model.ObjVal) if model.ObjVal is not None else None
    trucks_A_val = int(variables["trucks_A"].X)
    trucks_B_val = int(variables["trucks_B"].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": {
            "trucks_A": trucks_A_val,
            "trucks_B": trucks_B_val
        }
    }