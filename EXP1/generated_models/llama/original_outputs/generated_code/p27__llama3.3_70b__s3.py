import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    nodes = data['nodes']
    start_node = data['start_node']
    distance = data['distance']
    mtz_big_m = data['mtz_big_m']

    variables = {
        "x_1_2": model.addVar(vtype=gp.GRB.BINARY, name="x_1_2"),
        "x_1_3": model.addVar(vtype=gp.GRB.BINARY, name="x_1_3"),
        "x_1_4": model.addVar(vtype=gp.GRB.BINARY, name="x_1_4"),
        "x_1_5": model.addVar(vtype=gp.GRB.BINARY, name="x_1_5"),
        "x_1_6": model.addVar(vtype=gp.GRB.BINARY, name="x_1_6"),
        "x_1_7": model.addVar(vtype=gp.GRB.BINARY, name="x_1_7"),
        "x_2_1": model.addVar(vtype=gp.GRB.BINARY, name="x_2_1"),
        "x_2_3": model.addVar(vtype=gp.GRB.BINARY, name="x_2_3"),
        "x_2_4": model.addVar(vtype=gp.GRB.BINARY, name="x_2_4"),
        "x_2_5": model.addVar(vtype=gp.GRB.BINARY, name="x_2_5"),
        "x_2_6": model.addVar(vtype=gp.GRB.BINARY, name="x_2_6"),
        "x_2_7": model.addVar(vtype=gp.GRB.BINARY, name="x_2_7"),
        "x_3_1": model.addVar(vtype=gp.GRB.BINARY, name="x_3_1"),
        "x_3_2": model.addVar(vtype=gp.GRB.BINARY, name="x_3_2"),
        "x_3_4": model.addVar(vtype=gp.GRB.BINARY, name="x_3_4"),
        "x_3_5": model.addVar(vtype=gp.GRB.BINARY, name="x_3_5"),
        "x_3_6": model.addVar(vtype=gp.GRB.BINARY, name="x_3_6"),
        "x_3_7": model.addVar(vtype=gp.GRB.BINARY, name="x_3_7"),
        "x_4_1": model.addVar(vtype=gp.GRB.BINARY, name="x_4_1"),
        "x_4_2": model.addVar(vtype=gp.GRB.BINARY, name="x_4_2"),
        "x_4_3": model.addVar(vtype=gp.GRB.BINARY, name="x_4_3"),
        "x_4_5": model.addVar(vtype=gp.GRB.BINARY, name="x_4_5"),
        "x_4_6": model.addVar(vtype=gp.GRB.BINARY, name="x_4_6"),
        "x_4_7": model.addVar(vtype=gp.GRB.BINARY, name="x_4_7"),
        "x_5_1": model.addVar(vtype=gp.GRB.BINARY, name="x_5_1"),
        "x_5_2": model.addVar(vtype=gp.GRB.BINARY, name="x_5_2"),
        "x_5_3": model.addVar(vtype=gp.GRB.BINARY, name="x_5_3"),
        "x_5_4": model.addVar(vtype=gp.GRB.BINARY, name="x_5_4"),
        "x_5_6": model.addVar(vtype=gp.GRB.BINARY, name="x_5_6"),
        "x_5_7": model.addVar(vtype=gp.GRB.BINARY, name="x_5_7"),
        "x_6_1": model.addVar(vtype=gp.GRB.BINARY, name="x_6_1"),
        "x_6_2": model.addVar(vtype=gp.GRB.BINARY, name="x_6_2"),
        "x_6_3": model.addVar(vtype=gp.GRB.BINARY, name="x_6_3"),
        "x_6_4": model.addVar(vtype=gp.GRB.BINARY, name="x_6_4"),
        "x_6_5": model.addVar(vtype=gp.GRB.BINARY, name="x_6_5"),
        "x_6_7": model.addVar(vtype=gp.GRB.BINARY, name="x_6_7"),
        "x_7_1": model.addVar(vtype=gp.GRB.BINARY, name="x_7_1"),
        "x_7_2": model.addVar(vtype=gp.GRB.BINARY, name="x_7_2"),
        "x_7_3": model.addVar(vtype=gp.GRB.BINARY, name="x_7_3"),
        "x_7_4": model.addVar(vtype=gp.GRB.BINARY, name="x_7_4"),
        "x_7_5": model.addVar(vtype=gp.GRB.BINARY, name="x_7_5"),
        "x_7_6": model.addVar(vtype=gp.GRB.BINARY, name="x_7_6"),
        "u_2": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_2"),
        "u_3": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_3"),
        "u_4": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_4"),
        "u_5": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_5"),
        "u_6": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_6"),
        "u_7": model.addVar(vtype=gp.GRB.INTEGER, lb=1, ub=mtz_big_m, name="u_7")
    }

    # Objective function
    obj = gp.quicksum([distance[f"{i},{j}"] * variables[f"x_{i}_{j}"] for i in nodes for j in nodes if f"{i},{j}" in distance])
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraints
    model.addConstr(gp.quicksum([variables[f"x_{start_node}_{j}"] for j in nodes[1:]]), gp.GRB.EQUAL, 1)
    model.addConstr(gp.quicksum([variables[f"x_{i}_{start_node}"] for i in nodes[1:]]), gp.GRB.EQUAL, 1)

    for node in nodes[1:]:
        model.addConstr(gp.quicksum([variables[f"x_{node}_{j}"] for j in nodes if f"{node},{j}" in distance]), gp.GRB.EQUAL,
                         gp.quicksum([variables[f"x_{j}_{node}"] for j in nodes if f"{j},{node}" in distance]))

    model.addConstr(variables["u_2"] >= 1)
    model.addConstr(variables["u_3"] >= 1)
    model.addConstr(variables["u_4"] >= 1)
    model.addConstr(variables["u_5"] >= 1)
    model.addConstr(variables["u_6"] >= 1)
    model.addConstr(variables["u_7"] >= 1)

    for i in nodes[1:]:
        for j in nodes[1:]:
            if i != j:
                model.addConstr(variables[f"u_{i}"] - variables[f"u_{j}"] + mtz_big_m * (variables[f"x_{i}_{j}"] + variables[f"x_{j}_{i}"]) <= mtz_big_m - 1)

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }

    solution = {key: variables[key].X for key in variables}

    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }