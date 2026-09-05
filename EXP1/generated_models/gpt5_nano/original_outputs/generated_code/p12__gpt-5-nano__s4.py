import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model("SupplyLink")
    # Suppress solver output for cleaner runs
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

    # Decision variables
    y_vars = {}  # binary: open center
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y_vars[c] = var

    f_vars = {}  # continuous: shipment from center c to store s
    for c in centers:
        for s in stores:
            key = (c, s)
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
            f_vars[key] = var

    model.update()

    # Demand constraints: sum of shipments to each store equals its demand
    for s in stores:
        demand_s = data["demand"][s]
        model.addConstr(gp.quicksum(f_vars[(c, s)] for c in centers) == demand_s, name=f"Dem_{s}")

    # Capacity constraints: sum of shipments from each center <= capacity * open decision
    for c in centers:
        cap_c = data["capacity"][c]
        model.addConstr(gp.quicksum(f_vars[(c, s)] for s in stores) <= cap_c * y_vars[c], name=f"Cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    obj = gp.quicksum(opening_cost[c] * y_vars[c] for c in centers) + \
          gp.quicksum(transport_cost[c][s] * f_vars[(c, s)] for c in centers for s in stores)
    model.setObjective(obj, GRB.MINIMIZE)

    # Build the flat variables dictionary to return
    variables = {}
    for c in centers:
        key = f"y_{c}"
        variables[key] = y_vars[c]
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = f_vars[(c, s)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective_value = float(model.ObjVal)

    solution = {}
    for c in data["centers"]:
        key = f"y_{c}"
        solution[key] = variables[key].X
    for c in data["centers"]:
        for s in data["stores"]:
            key = f"f_{c}_{s}"
            solution[key] = variables[key].X

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }