import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Read per-truck yields from data
    truck_contents = data.get("truck_contents", {})
    A_yields = truck_contents.get("A", {})
    B_yields = truck_contents.get("B", {})

    a_A = int(A_yields.get("A", 0))
    a_B = int(A_yields.get("B", 0))
    a_C = int(A_yields.get("C", 0))

    b_A = int(B_yields.get("A", 0))
    b_B = int(B_yields.get("B", 0))
    b_C = int(B_yields.get("C", 0))

    # Demands (can be overridden if provided in data)
    A_req = int(data.get("demand_A", 240))
    B_req = int(data.get("demand_B", 80))
    C_req = int(data.get("demand_C", 120))

    # Freight costs
    freight = data.get("freight_cost", {})
    cost_A = float(freight.get("A", 200))
    cost_B = float(freight.get("B", 160))

    # Decision variables
    trucks_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_A")
    trucks_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="trucks_B")

    # Constraints
    model.addConstr(a_A * trucks_A + b_A * trucks_B >= A_req, name="A_requirement")
    model.addConstr(a_B * trucks_A + b_B * trucks_B >= B_req, name="B_requirement")
    model.addConstr(a_C * trucks_A + b_C * trucks_B >= C_req, name="C_requirement")

    # Objective
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
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CUTOFF: "CUTOFF",
        GRB.POSSIBLE_SOLUTION: "POSSIBLE_SOLUTION",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
    }
    status_str = status_map.get(status_code, str(status_code))

    model.update()

    objective_value = float(model.ObjVal)

    trA = int(variables["trucks_A"].X)
    trB = int(variables["trucks_B"].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": {
            "trucks_A": trA,
            "trucks_B": trB
        }
    }