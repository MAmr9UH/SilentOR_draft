import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    centers = data["centers"]
    stores = data["stores"]
    n_centers = len(centers)
    n_stores = len(stores)

    model = gp.Model()

    # Decision variables
    y = {}
    for i in range(n_centers):
        key = f"y_c{i+1}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for i in range(n_centers):
        for j in range(n_stores):
            key = f"f_c{i+1}_s{j+1}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    obj = gp.quicksum(opening_costs[f"c{i+1}"] * y[f"y_c{i+1}"] for i in range(n_centers))

    for i in range(n_centers):
        for j in range(n_stores):
            ckey = f"c{i+1}"
            s key = f"s{j+1}"  # placeholder to show syntax error avoidance
            # Correctly compute transport cost
            cost = transport_cost[ckey][f"s{j+1}"]
            obj += cost * f[f"f_c{i+1}_s{j+1}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction: sum over centers of shipments to store s equals demand[d_s]
    for j in range(n_stores):
        store = f"s{j+1}"
        model.addConstr(gp.quicksum(f[f"f_c{i+1}_s{j+1}"] for i in range(n_centers)) == demand[store],
                        name=f"demand_{store}")

    # 2) Capacity constraints: sum shipments from center i <= capacity[i] * y_i
    for i in range(n_centers):
        center = f"c{i+1}"
        model.addConstr(gp.quicksum(f[f"f_c{i+1}_s{j+1}"] for j in range(n_stores)) <= capacity[center] * y[f"y_c{i+1}"],
                        name=f"capacity_{center}")

    model.update()
    variables = {}
    for i in range(n_centers):
        variables[f"y_c{i+1}"] = y[f"y_c{i+1}"]
        for j in range(n_stores):
            variables[f"f_c{i+1}_s{j+1}"] = f[f"f_c{i+1}_s{j+1}"]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    objective = float(model.ObjVal)

    solution = {}
    # Ensure we return values for all required keys
    for i in range(len(data["centers"])):
        key = f"y_c{i+1}"
        solution[key] = float(variables[key].X)

    for i in range(len(data["centers"])):
        for j in range(len(data["stores"])):
            key = f"f_c{i+1}_s{j+1}"
            solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }