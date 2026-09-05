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
    
    for branch in data["branches"]:
        for specialty in data["specialties"]:
            demand_var = gp.quicksum([variables[f"x_{type}_{branch}_{specialty}"] for type in data["types"] if specialty in data["suitable_specialties"][str(type)]])
            model.addConstr(demand_var == data["demand"][f"{branch}_{specialty}"])
    
    for type in data["types"]:
        supply_var = gp.quicksum([variables[f"x_{type}_{branch}_{specialty}"] for branch in data["branches"] for specialty in data["suitable_specialties"][str(type)]])
        model.addConstr(supply_var <= data["available_people"][str(type)])
    
    p2_preferred_specialty_sum = gp.quicksum([variables[f"x_{type}_{branch}_{data['preferred_specialty'][str(type)]}"] for type in data["types"] for branch in data["branches"] if data["preferred_specialty"][str(type)] in data["suitable_specialties"][str(type)]])
    model.addConstr(p2_preferred_specialty_sum >= 0)
    
    p3_preferred_city_sum = gp.quicksum([variables[f"x_{type}_{data['preferred_city'][str(type)]}_{specialty}"] for type in data["types"] for specialty in data["suitable_specialties"][str(type)]])
    model.addConstr(p3_shortfall == max(0, data["p3_preferred_city_target"] - p3_preferred_city_sum))
    
    model.setObjectiveN(p3_shortfall, 1, weight=1)
    model.ModelSense = gp.GRB.MINIMIZE
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    solution = {}
    for var_name in variables.keys():
        if isinstance(variables[var_name], gp.Var):
            solution[var_name] = variables[var_name].X
        else:
            raise ValueError("Unexpected variable type")
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    result = {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }
    
    return result