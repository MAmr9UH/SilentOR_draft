import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    cap = data["cap"]
    dem = data["dem"]
    vcost = data["vcost"]
    fixed = data["fixed"]

    # Decision variables
    produced = {}
    for i in range(1, 7):
        produced[str(i)] = model.addVar(lb=0, vtype=GRB.INTEGER, name=f"produced_{i}")

    allocation = {}
    for i in range(1, 7):
        for j in range(1, 7):
            if cap[i-1] >= cap[j-1]:
                allocation[str(i) + "," + str(j)] = model.addVar(lb=0, vtype=GRB.INTEGER, name=f"allocation_{i}_{j}")

    # Objective function
    model.setObjective(gp.quicksum(vcost[i-1] * produced[str(i)] for i in range(1, 7)) +
                       gp.quicksum(allocation[str(i) + "," + str(j)] * vcost[j-1] for i in range(1, 7) for j in range(1, 7) if cap[i-1] >= cap[j-1]) +
                       fixed * len(produced) , GRB.MINIMIZE)

    # Constraints
    for j in range(1, 7):
        model.addConstr(gp.quicksum(allocation[str(i) + "," + str(j)] for i in range(1, 7) if cap[i-1] >= cap[j-1]) + produced[str(j)] >= dem[j-1], name=f"demand_{j}")

    variables = {
        "produced": produced,
        "allocation": allocation
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    produced_solution = {}
    for i in range(1, 7):
        produced_solution[str(i)] = float(variables["produced"][str(i)].X)

    allocation_solution = {}
    for i in range(1, 7):
        for j in range(1, 7):
            if data["cap"][i-1] >= data["cap"][j-1]:
                allocation_solution[str(i) + "," + str(j)] = float(variables["allocation"][str(i) + "," + str(j)].X)

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": {
            "produced": produced_solution,
            "allocation": allocation_solution
        }
    }