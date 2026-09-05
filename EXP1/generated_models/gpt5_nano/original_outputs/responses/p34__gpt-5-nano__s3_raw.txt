import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()

    # Decision variables: integer number of trucks from A and B
    trucks_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    # Extract data components
    contents = data.get("truck_contents", {})
    A_contents = contents.get("A", {})
    B_contents = contents.get("B", {})

    # Demands (with safe defaults from problem text; can be overridden by data["requirements"])
    reqs = data.get("requirements", {})
    min_A = int(reqs.get("A", 240))
    min_B = int(reqs.get("B", 80))
    min_C = int(reqs.get("C", 120))

    # Coefficients for raw materials
    A_to_A = A_contents.get("A", 0)  # raw material A delivered by A-truck
    A_to_B = B_contents.get("A", 0)  # raw material A delivered by B-truck

    B_to_A = A_contents.get("B", 0)  # raw material B delivered by A-truck
    B_to_B = B_contents.get("B", 0)  # raw material B delivered by B-truck

    C_to_A = A_contents.get("C", 0)  # raw material C delivered by A-truck
    C_to_B = B_contents.get("C", 0)  # raw material C delivered by B-truck

    # Constraints: supply minimums
    model.addConstr(A_to_A * trucks_A + A_to_B * trucks_B >= min_A, name="A_min")
    model.addConstr(B_to_A * trucks_A + B_to_B * trucks_B >= min_B, name="B_min")
    model.addConstr(C_to_A * trucks_A + C_to_B * trucks_B >= min_C, name="C_min")

    # Objective: minimize total freight cost
    cost_A = data.get("freight_cost", {}).get("A", 0)
    cost_B = data.get("freight_cost", {}).get("B", 0)
    model.setObjective(cost_A * trucks_A + cost_B * trucks_B, GRB.MINIMIZE)

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = float(model.ObjVal)

    solution = {
        "trucks_A": int(variables["trucks_A"].X),
        "trucks_B": int(variables["trucks_B"].X)
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }