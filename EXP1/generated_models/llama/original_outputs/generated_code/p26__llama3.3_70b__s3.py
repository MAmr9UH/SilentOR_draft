import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for student in data["students"]:
        for day in data["days"]:
            variables[f"h_{student}_{day}"] = model.addVar(lb=0, ub=data["availability_hours"][str(student)][day], vtype=gp.GRB.CONTINUOUS)
            variables[f"y_{student}_{day}"] = model.addVar(vtype=gp.GRB.BINARY)
    
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for student in data["students"]) == data["open_hours_per_day"])
        
    for student in data["undergraduates"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for day in data["days"]) >= data["minimum_weekly_hours_undergrad"])
    
    for student in data["graduates"]:
        model.addConstr(gp.quicksum(variables[f"h_{student}_{day}"] for day in data["days"]) >= data["minimum_weekly_hours_grad"])
        
    for student in data["students"]:
        model.addConstr(gp.quicksum(variables[f"y_{student}_{day}"] for day in data["days"]) <= data["max_shifts_per_week"])
    
    for day in data["days"]:
        model.addConstr(gp.quicksum(variables[f"y_{student}_{day}"] for student in data["students"]) <= data["max_students_per_day"])
        
    for student in data["students"]:
        for day in data["days"]:
            model.addConstr(variables[f"h_{student}_{day}"] <= variables[f"y_{student}_{day}"] * data["availability_hours"][str(student)][day])
    
    objective = gp.quicksum(data["wage"][str(student)] * variables[f"h_{student}_{day}"] for student in data["students"] for day in data["days"])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    solution = {}
    for var_key in ["h_1_Mon", "h_1_Tue", "h_1_Wed", "h_1_Thu", "h_1_Fri",
                    "h_2_Mon", "h_2_Tue", "h_2_Wed", "h_2_Thu", "h_2_Fri",
                    "h_3_Mon", "h_3_Tue", "h_3_Wed", "h_3_Thu", "h_3_Fri",
                    "h_4_Mon", "h_4_Tue", "h_4_Wed", "h_4_Thu", "h_4_Fri",
                    "h_5_Mon", "h_5_Tue", "h_5_Wed", "h_5_Thu", "h_5_Fri",
                    "h_6_Mon", "h_6_Tue", "h_6_Wed", "h_6_Thu", "h_6_Fri",
                    "y_1_Mon", "y_1_Tue", "y_1_Wed", "y_1_Thu", "y_1_Fri",
                    "y_2_Mon", "y_2_Tue", "y_2_Wed", "y_2_Thu", "y_2_Fri",
                    "y_3_Mon", "y_3_Tue", "y_3_Wed", "y_3_Thu", "y_3_Fri",
                    "y_4_Mon", "y_4_Tue", "y_4_Wed", "y_4_Thu", "y_4_Fri",
                    "y_5_Mon", "y_5_Tue", "y_5_Wed", "y_5_Thu", "y_5_Fri",
                    "y_6_Mon", "y_6_Tue", "y_6_Wed", "y_6_Thu", "y_6_Fri"]:
        solution[var_key] = model.getVarByName(var_key).X
    
    status_map = {gp.GRB.OPTIMAL: "OPTIMAL", gp.GRB.INFEASIBLE: "INFEASIBLE", 
                  gp.GRB.UNBOUNDED: "UNBOUNDED", gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
                  gp.GRB.TIME_LIMIT: "TIME_LIMIT"}
    status = status_map[model.Status]
    
    return {"status": status, "objective": model.ObjVal, "solution": solution}