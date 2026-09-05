import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for type in data["types"]:
        for branch in data["branches"]:
            for specialty in data["suitable_specialties"][str(type)]:
                var_name = f"x_{type}_{branch}_{specialty}"
                variables[var_name] = model.addVar(lb=0, ub=data["available_people"][str(type)], vtype=gp.GRB.INTEGER)
    
    p3_shortfall = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    variables["p3_shortfall"] = p3_shortfall
    
    # Demand constraints
    for branch in data["branches"]:
        for specialty in data["specialties"]:
            demand_var = gp.quicksum(variables[f"x_{type}_{branch}_{specialty}"] for type in data["types"] if specialty in data["suitable_specialties"][str(type)])
            model.addConstr(demand_var == data["demand"][f"{branch}_{specialty}"])
    
    # Availability constraints
    for type in data["types"]:
        availability_var = gp.quicksum(variables[f"x_{type}_{branch}_{specialty}"] for branch in data["branches"] for specialty in data["suitable_specialties"][str(type)])
        model.addConstr(availability_var <= data["available_people"][str(type)])
    
    # Objective: Lexicographic goal programming
    model.setObjectiveN(p3_shortfall, 0)
    
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