import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()
    # Optional: silence solver output if desired
    # model.setParam('OutputFlag', 0)

    variables = {}

    # Opening decisions for centers: y_c
    for c in data["centers"]:
        key = f"y_{c}"
        var = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = var

    # Transportation decisions: f_c_s
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            ub = data["demand"][s]
            var = model.addVar(lb=0.0, ub=ub, vtype=GRB.CONTINUOUS, name=key)
            variables[key] = var

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_cost_term = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in data["centers"])
    transport_cost_term = gp.quicksum(
        data["transport_cost"][c][s] * variables[f"f_{c}_{s}"]
        for c in data["centers"]
        for s in data["stores"]
    )
    model.setObjective(opening_cost_term + transport_cost_term, GRB.MINIMIZE)

    # Constraints
    # Demand satisfaction for each store: sum_c f_c_s == demand_s
    for s in data["stores"]:
        model.addConstr(
            gp.quicksum(variables[f"f_{c}_{s}"] for c in data["centers"]) == data["demand"][s],
            name=f"dem_{s}"
        )

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in data["centers"]:
        model.addConstr(
            gp.quicksum(variables[f"f_{c}_{s}"] for s in data["stores"]) <= data["capacity"][c] * variables[f"y_{c}"],
            name=f"cap_{c}"
        )

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.CUTOFF: "CUTOFF",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status, str(status))

    objective = float(model.ObjVal)

    solution = {}
    # y variables
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    # f_c_s variables
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }