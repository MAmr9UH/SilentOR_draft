import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()
    # Decision variables: integer number of trucks from each warehouse
    trucks_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    # Data extraction (assumes the provided data schema)
    A_need = 240
    B_need = 80
    C_need = 120

    A_from_A = data["truck_contents"]["A"]["A"]
    A_from_B = data["truck_contents"]["B"]["A"]

    B_from_A = data["truck_contents"]["A"]["B"]
    B_from_B = data["truck_contents"]["B"]["B"]

    C_from_A = data["truck_contents"]["A"]["C"]
    C_from_B = data["truck_contents"]["B"]["C"]

    cost_A = data["freight_cost"]["A"]
    cost_B = data["freight_cost"]["B"]

    # Objective: minimize total freight cost
    model.setObjective(cost_A * trucks_A + cost_B * trucks_B, GRB.MINIMIZE)

    # Constraints: meet all material requirements
    model.addConstr(A_from_A * trucks_A + A_from_B * trucks_B >= A_need)
    model.addConstr(B_from_A * trucks_A + B_from_B * trucks_B >= B_need)
    model.addConstr(C_from_A * trucks_A + C_from_B * trucks_B >= C_need)

    model.update()
    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }
    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_value = model.Status
    if status_value == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_value == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_value == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_value == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_value == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_value)

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