import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "x_1_1": model.addVar(vtype=gp.GRB.INTEGER),
        "x_1_2": model.addVar(vtype=gp.GRB.INTEGER),
        "x_1_3": model.addVar(vtype=gp.GRB.INTEGER),
        "x_1_4": model.addVar(vtype=gp.GRB.INTEGER),
        "x_2_1": model.addVar(vtype=gp.GRB.INTEGER),
        "x_2_2": model.addVar(vtype=gp.GRB.INTEGER),
        "x_2_3": model.addVar(vtype=gp.GRB.INTEGER),
        "x_3_1": model.addVar(vtype=gp.GRB.INTEGER),
        "x_3_2": model.addVar(vtype=gp.GRB.INTEGER),
        "x_4_1": model.addVar(vtype=gp.GRB.INTEGER),
        "y_1": model.addVar(vtype=gp.GRB.BINARY),
        "y_2": model.addVar(vtype=gp.GRB.BINARY),
        "y_3": model.addVar(vtype=gp.GRB.BINARY),
        "y_4": model.addVar(vtype=gp.GRB.BINARY)
    }
    
    # Objective function
    objective = gp.quicksum([variables["x_1_1"] * data["fee_per_100sqm_by_length"]["1"],
                             variables["x_1_2"] * data["fee_per_100sqm_by_length"]["2"],
                             variables["x_1_3"] * data["fee_per_100sqm_by_length"]["3"],
                             variables["x_1_4"] * data["fee_per_100sqm_by_length"]["4"],
                             variables["x_2_1"] * data["fee_per_100sqm_by_length"]["1"],
                             variables["x_2_2"] * data["fee_per_100sqm_by_length"]["2"],
                             variables["x_2_3"] * data["fee_per_100sqm_by_length"]["3"],
                             variables["x_3_1"] * data["fee_per_100sqm_by_length"]["1"],
                             variables["x_3_2"] * data["fee_per_100sqm_by_length"]["2"],
                             variables["x_4_1"] * data["fee_per_100sqm_by_length"]["1"]])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    # Constraints
    model.addConstr(variables["x_1_1"] + variables["x_2_1"] >= data["demand_100sqm"]["1"])
    model.addConstr(variables["x_1_2"] + variables["x_1_3"] + variables["x_2_2"] + variables["x_3_1"] >= data["demand_100sqm"]["2"])
    model.addConstr(variables["x_1_3"] + variables["x_1_4"] + variables["x_2_3"] + variables["x_3_2"] >= data["demand_100sqm"]["3"])
    model.addConstr(variables["x_1_4"] + variables["x_4_1"] >= data["demand_100sqm"]["4"])
    
    # At least two different contract lengths must be signed
    model.addConstr(gp.quicksum([variables["y_1"], variables["y_2"], variables["y_3"], variables["y_4"]]) >= data["min_distinct_lengths"])
    
    # The number of distinct warehouse contract lengths signed cannot exceed 3
    model.addConstr(gp.quicksum([variables["y_1"], variables["y_2"], variables["y_3"], variables["y_4"]]) <= data["max_distinct_lengths"])
    
    # If a 4-month contract is chosen, then no 1-month contract may be chosen
    model.addConstr(variables["x_1_4"] + variables["x_4_1"] <= (data["months"][3] - data["months"][0] + 1) * variables["y_4"])
    model.addConstr(variables["x_1_1"] + variables["x_2_1"] + variables["x_3_1"] + variables["x_4_1"] <= (data["months"][3] - data["months"][0] + 1) * (1 - variables["y_4"]))
    
    # Binary constraints
    model.addConstr(variables["x_1_1"] >= variables["y_1"])
    model.addConstr(variables["x_1_2"] >= variables["y_2"])
    model.addConstr(variables["x_1_3"] >= variables["y_3"])
    model.addConstr(variables["x_1_4"] >= variables["y_4"])
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    solution = {
        "status": None,
        "objective": None,
        "solution": {}
    }
    
    if model.Status == gp.GRB.OPTIMAL:
        solution["status"] = "OPTIMAL"
        solution["objective"] = model.ObjVal
        for key, var in variables.items():
            solution["solution"][key] = var.X
    elif model.Status == gp.GRB.INFEASIBLE:
        solution["status"] = "INFEASIBLE"
    elif model.Status == gp.GRB.UNBOUNDED:
        solution["status"] = "UNBOUNDED"
    elif model.Status == gp.GRB.INF_OR_UNBD:
        solution["status"] = "INF_OR_UNBD"
    elif model.Status == gp.GRB.TIME_LIMIT:
        solution["status"] = "TIME_LIMIT"
    
    return solution