import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    centers = data["centers"]
    stores = data["stores"]

    # Decision variables
    variables = {}

    # Opening decision variables y_c1 ... y_c5
    for c_label in centers:
        key = f"y_{c_label}"
        variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # Shipment variables f_cX_sY
    for c_label in centers:
        for s_label in stores:
            key = f"f_{c_label}_{s_label}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Demand constraints: sum_i f_i_j == demand_j
    for s_label in stores:
        demand = data["demand"][s_label]
        model.addConstr(gp.quicksum(variables[f"f_{c_label}_{s_label}"] for c_label in centers) == demand,
                        name=f"Demand_{s_label}")

    # Capacity constraints: sum_j f_i_j <= capacity_i * y_i
    for c_label in centers:
        cap = data["capacity"][c_label]
        model.addConstr(gp.quicksum(variables[f"f_{c_label}_{s_label}"] for s_label in stores) <=
                        cap * variables[f"y_{c_label}"],
                        name=f"Cap_{c_label}")

    # Objective: minimize total opening + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_costs = data["transport_cost"]

    open_cost_term = gp.quicksum(opening_costs[c_label] * variables[f"y_{c_label}"] for c_label in centers)
    transport_cost_term = gp.quicksum(transport_costs[c_label][s_label] * variables[f"f_{c_label}_{s_label}"]
                                      for c_label in centers for s_label in stores)

    model.setObjective(open_cost_term + transport_cost_term, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    objective_value = float(model.ObjVal)

    solution = {}
    # y variables
    for c_label in data["centers"]:
        key = f"y_{c_label}"
        solution[key] = variables[key].X
    # f variables
    for c_label in data["centers"]:
        for s_label in data["stores"]:
            key = f"f_{c_label}_{s_label}"
            solution[key] = variables[key].X

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }