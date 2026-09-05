import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model along with a dictionary of all decision variables
    using the exact keys specified in the problem statement.
    """
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    y = {}  # center open decision variables
    variables = {}

    # Binary opening variables
    for c in centers:
        var = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")
        y[c] = var
        variables[f"y_{c}"] = var

    # Shipment variables f_c_s
    f = {}
    for c in centers:
        for s in stores:
            var = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")
            f[(c, s)] = var
            variables[f"f_{c}_{s}"] = var

    # Data
    opening_cost = data["fixed_opening_cost"]      # dict: c1 -> cost
    transport_cost = data["transport_cost"]        # dict: c -> {s -> cost}
    demand = data["demand"]                        # dict: s -> demand
    capacity = data["capacity"]                    # dict: c -> capacity

    # Objective: minimize opening costs + transport costs
    opening_term = gp.quicksum(opening_cost[c] * y[c] for c in centers)
    transport_term = gp.quicksum(transport_cost[c][s] * f[(c, s)] for c in centers for s in stores)
    model.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction for each store
    for s in stores:
        model.addConstr(gp.quicksum(f[(c, s)] for c in centers) == demand[s], name=f"dem_{s}")

    # 2) Capacity constraints: shipments from a center cannot exceed capacity if opened
    for c in centers:
        model.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= capacity[c] * y[c], name=f"cap_{c}")

    model.update()
    return model, variables


def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the structured solution dict.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    objective = float(model.ObjVal)

    # The exact order required by the schema
    keys_order = [
        "y_c1","y_c2","y_c3","y_c4","y_c5","y_c6",
        "f_c1_s1","f_c1_s2","f_c1_s3","f_c1_s4","f_c1_s5","f_c1_s6","f_c1_s7",
        "f_c2_s1","f_c2_s2","f_c2_s3","f_c2_s4","f_c2_s5","f_c2_s6","f_c2_s7",
        "f_c3_s1","f_c3_s2","f_c3_s3","f_c3_s4","f_c3_s5","f_c3_s6","f_c3_s7",
        "f_c4_s1","f_c4_s2","f_c4_s3","f_c4_s4","f_c4_s5","f_c4_s6","f_c4_s7",
        "f_c5_s1","f_c5_s2","f_c5_s3","f_c5_s4","f_c5_s5","f_c5_s6","f_c5_s7",
        "f_c6_s1","f_c6_s2","f_c6_s3","f_c6_s4","f_c6_s5","f_c6_s6","f_c6_s7"
    ]

    solution = {}
    for key in keys_order:
        solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }