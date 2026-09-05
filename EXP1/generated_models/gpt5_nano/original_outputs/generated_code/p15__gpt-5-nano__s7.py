import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()

    centers = data["centers"]  # e.g., ["c1", "c2", "c3", "c4", "c5"]
    stores = data["stores"]    # e.g., ["s1", "s2", ..., "s7"]

    # Decision variables
    y_vars = []
    for i in range(len(centers)):
        y = model.addVar(vtype=GRB.BINARY, name=f"y_c{i+1}")
        y_vars.append(y)

    f_vars = {}
    for i in range(len(centers)):
        for j in range(len(stores)):
            f = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"f_c{i+1}_s{j+1}")
            f_vars[(i, j)] = f

    model.update()

    # Demand constraints: sum_i f_i_j == demand_j
    for j, s in enumerate(stores):
        demand = data["demand"][s]
        model.addConstr(quicksum(f_vars[(i, j)] for i in range(len(centers))) == demand,
                        name=f"dem_{s}")

    # Capacity constraints: sum_j f_i_j <= capacity_i * y_i
    for i, c in enumerate(centers):
        capacity = data["capacity"][c]
        model.addConstr(quicksum(f_vars[(i, j)] for j in range(len(stores))) <= capacity * y_vars[i],
                        name=f"cap_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    obj = quicksum(opening_costs[f"c{i+1}"] * y_vars[i] for i in range(len(centers)))

    for i in range(len(centers)):
        for j in range(len(stores)):
            cost = data["transport_cost"][f"c{i+1}"][f"s{j+1}"]
            obj += cost * f_vars[(i, j)]

    model.setObjective(obj, GRB.MINIMIZE)

    # Export variables in required flat key format
    variables = {}
    for i in range(len(centers)):
        variables[f"y_c{i+1}"] = y_vars[i]
    for i in range(len(centers)):
        for j in range(len(stores)):
            variables[f"f_c{i+1}_s{j+1}"] = f_vars[(i, j)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status

    def status_to_string(code):
        if code == GRB.OPTIMAL:
            return "OPTIMAL"
        if code == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if code == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if code == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if code == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        if code == GRB.SUBOPTIMAL:
            return "SUBOPTIMAL"
        if code == GRB.CUT:
            return "CUT"
        return str(code)

    status_str = status_to_string(status_code)

    model.update()
    objective_value = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }