import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build and return the Gurobi model and the decision variables.

    Returns:
        model: gurobipy Model object
        variables: dict with keys "trucks_A" and "trucks_B" mapping to their Var objects
    """
    model = gp.Model()

    # Extract data with reasonable defaults (if some fields are missing)
    truck_contents = data.get("truck_contents", {})
    A_contents = truck_contents.get("A", {})
    B_contents = truck_contents.get("B", {})

    # Coefficients per truck from each warehouse
    aA = A_contents.get("A", 4)  # raw material A per truck from A
    aB = A_contents.get("B", 2)  # raw material B per truck from A
    aC = A_contents.get("C", 6)  # raw material C per truck from A

    bA = B_contents.get("A", 7)  # raw material A per truck from B
    bB = B_contents.get("B", 2)  # raw material B per truck from B
    bC = B_contents.get("C", 2)  # raw material C per truck from B

    # Demands (hard-coded as per problem statement; could be read from data if provided)
    req_A = 240  # pieces of raw material A
    req_B = 80   # kg of raw material B
    req_C = 120  # tons of raw material C

    # Freight costs per truck
    freight = data.get("freight_cost", {})
    cost_A = freight.get("A", 200)
    cost_B = freight.get("B", 160)

    # Decision variables
    trucks_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    # Constraints: meet daily material requirements
    model.addConstr(aA * trucks_A + bA * trucks_B >= req_A, name="A_requirement")
    model.addConstr(aB * trucks_A + bB * trucks_B >= req_B, name="B_requirement")
    model.addConstr(aC * trucks_A + bC * trucks_B >= req_C, name="C_requirement")

    # Objective: minimize total freight cost
    model.setObjective(cost_A * trucks_A + cost_B * trucks_B, sense=GRB.MINIMIZE)

    model.update()

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to human-readable string
    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None
    trucks_A_val = int(variables["trucks_A"].X) if variables["trucks_A"] is not None else None
    trucks_B_val = int(variables["trucks_B"].X) if variables["trucks_B"] is not None else None

    result = {
        "status": status_str,
        "objective": obj_val,
        "solution": {
            "trucks_A": trucks_A_val,
            "trucks_B": trucks_B_val
        }
    }

    return result