import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    for type in data["types"]:
        for branch in data["branches"]:
            for specialty in data["suitable_specialties"][str(type)]:
                var_name = f"x_{type}_{branch}_{specialty}"
                variables[var_name] = model.addVar(lb=0, ub=data["available_people"][str(type)], vtype=gp.GRB.INTEGER)
    
    p3_shortfall = model.addVar(lb=0, vtype=gp.GRB.INTEGER)
    variables["p3_shortfall"] = p3_shortfall
    
    # Demand constraints
    for branch in data["branches"]:
        for specialty in data["specialties"]:
            demand_var_name = f"{branch}_{specialty}"
            if demand_var_name not in data["demand"]:
                continue
            demand = data["demand"][demand_var_name]
            var_sum = gp.quicksum(variables[f"x_{type}_{branch}_{specialty}"] for type in data["types"] if specialty in data["suitable_specialties"][str(type)])
            model.addConstr(var_sum == demand, name=f"demand_{branch}_{specialty}")
    
    # Availability constraints
    for type in data["types"]:
        var_sum = gp.quicksum(variables[f"x_{type}_{branch}_{specialty}"] for branch in data["branches"] for specialty in data["suitable_specialties"][str(type)])
        model.addConstr(var_sum <= data["available_people"][str(type)], name=f"availability_{type}")
    
    # Objective: minimize p3_shortfall
    model.setObjective(p3_shortfall, gp.GRB.MINIMIZE)
    
    # P2 preferred specialty target constraint (not used in this problem)
    # p2_preferred_specialty_target = data["p2_preferred_specialty_target"]
    # var_sum = gp.quicksum(variables[f"x_{type}_{branch}_{data['preferred_specialty'][str(type)]}"] for type in data["types"] for branch in data["branches"])
    # model.addConstr(var_sum >= p2_preferred_specialty_target, name="p2_preferred_specialty")
    
    # P3 preferred city target constraint
    p3_preferred_city_target = data["p3_preferred_city_target"]
    var_sum = gp.quicksum(variables[f"x_{type}_{data['preferred_city'][str(type)]}_{specialty}"] for type in data["types"] for specialty in data["suitable_specialties"][str(type)])
    model.addConstr(var_sum + p3_shortfall == p3_preferred_city_target, name="p3_preferred_city")
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status = None
    if model.Status == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif model.Status == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif model.Status == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif model.Status == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif model.Status == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    
    solution = {var_name: var.X for var_name, var in variables.items()}
    objective = model.ObjVal
    
    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }