import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    """
    Builds and returns the Gurobi model and a flat mapping of all decision variables
    with exactly the keys specified in the problem statement.
    """
    m = gp.Model()
    m.setParam('OutputFlag', 0)

    centers = data['centers']        # e.g., ['c1','c2','c3','c4']
    stores = data['stores']          # e.g., ['s1','s2','s3','s4','s5','s6']
    opening_cost = data['fixed_opening_cost']  # dict: {'c1': cost, ...}
    transport_cost = data['transport_cost']    # dict: {'c1': {'s1': cost, ...}, ...}
    demand = data['demand']            # dict: {'s1': val, ...}
    capacity = data['capacity']        # dict: {'c1': cap, ...}

    n_centers = len(centers)
    n_stores = len(stores)

    # Decision variables
    # y_c: binary open indicator for each center
    y_vars = {}
    for i in range(1, n_centers + 1):
        y_vars[i] = m.addVar(vtype=GRB.BINARY, name=f"y_c{i}")

    # f_c_s: continuous shipment from center c to store s
    f_vars = {}
    for i in range(1, n_centers + 1):
        for j in range(1, n_stores + 1):
            var_name = f"f_c{i}_s{j}"
            f_vars[(i, j)] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=var_name)

    m.update()

    # Objective: minimize opening costs + transportation costs
    opening_term = quicksum(opening_cost[centers[i-1]] * y_vars[i] for i in range(1, n_centers + 1))
    transport_term = quicksum(
        transport_cost[centers[i-1]][stores[j-1]] * f_vars[(i, j)]
        for i in range(1, n_centers + 1)
        for j in range(1, n_stores + 1)
    )
    m.setObjective(opening_term + transport_term, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction: sum_c f_c_s = demand_s for each store s
    for j in range(1, n_stores + 1):
        m.addConstr(
            quicksum(f_vars[(i, j)] for i in range(1, n_centers + 1)) == demand[stores[j-1]]
        )

    # 2) Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for i in range(1, n_centers + 1):
        center_name = centers[i-1]
        m.addConstr(
            quicksum(f_vars[(i, j)] for j in range(1, n_stores + 1)) <= capacity[center_name] * y_vars[i]
        )

    # Prepare variables dictionary to return (flat keys exactly as required)
    variables = {}
    for i in range(1, n_centers + 1):
        variables[f"y_c{i}"] = y_vars[i]
    for i in range(1, n_centers + 1):
        for j in range(1, n_stores + 1):
            variables[f"f_c{i}_s{j}"] = f_vars[(i, j)]

    return m, variables

def solve(data: dict):
    """
    Builds, solves, and returns the solution in the required format.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string as required by the schema (OPTIMAL, etc.)
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.CONTINUING: "CONTINUING"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective_val = float(model.ObjVal)

    # Build solution dict with exact keys and values
    solution = {}
    # y variables
    for i in range(1, len(data['centers']) + 1):
        key = f"y_c{i}"
        solution[key] = float(variables[key].X)

    # f variables
    for i in range(1, len(data['centers']) + 1):
        for j in range(1, len(data['stores']) + 1):
            key = f"f_c{i}_s{j}"
            solution[key] = float(variables[key].X)

    result = {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }

    return result