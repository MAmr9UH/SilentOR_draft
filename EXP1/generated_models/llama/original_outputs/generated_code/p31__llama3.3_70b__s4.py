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
            demand_var_name = f"{branch}_{specialty}"
            if demand_var_name not in data["demand"]:
                continue
            demand = data["demand"][demand_var_name]
            assigned_people = gp.quicksum([variables[f"x_{type}_{branch}_{specialty}"] for type in data["types"] if specialty in data["suitable_specialties"][str(type)]])
            model.addConstr(assigned_people == demand, name=f"meet_demand_{branch}_{specialty}")
    
    p2_preferred_specialty_target = 0
    for type in data["types"]:
        preferred_specialty = data["preferred_specialty"][str(type)]
        assigned_to_preferred_specialty = gp.quicksum([variables[f"x_{type}_{branch}_{preferred_specialty}"] for branch in data["branches"] if preferred_specialty in data["suitable_specialties"][str(type)]])
        p2_preferred_specialty_target += assigned_to_preferred_specialty
    
    model.addConstr(p3_shortfall >= 0, name="p3_shortfall_non_negative")
    
    p3_preferred_city_assignments = gp.quicksum([variables[f"x_{type}_{branch}_{specialty}"] for type in data["types"] for branch in data["branches"] for specialty in data["suitable_specialties"][str(type)] if branch == data["preferred_city"][str(type)]])
    
    model.addConstr(p3_shortfall >= data["p3_preferred_city_target"] - p3_preferred_city_assignments, name="meet_p3_target")
    
    model.setObjectiveN(p3_shortfall, 0, weight=1.0)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_to_string = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {}
    for var_name in variables:
        if isinstance(variables[var_name], dict):
            for inner_var_name, var in variables[var_name].items():
                solution[inner_var_name] = var.X
        else:
            solution[var_name] = variables[var_name].X
    
    return {
        "status": status_to_string[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }