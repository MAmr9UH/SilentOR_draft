import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "x_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    }
    
    # Production constraints
    model.addConstr(variables["x_I_2"] == 0)  # Product I cannot be produced in quarter 2
    
    for q in data["quarters"]:
        if q == 1:
            model.addConstr(variables[f"Iv_I_{q}"] - variables[f"x_I_{q}"] + variables[f"Bk_I_{q}"] == data["orders"][f"I_{q}"])
            model.addConstr(variables[f"Iv_II_{q}"] - variables[f"x_II_{q}"] + variables[f"Bk_II_{q}"] == data["orders"][f"II_{q}"])
            model.addConstr(variables[f"Iv_III_{q}"] - variables[f"x_III_{q}"] + variables[f"Bk_III_{q}"] == data["orders"][f"III_{q}"])
        else:
            model.addConstr(variables[f"Iv_I_{q}"] - variables[f"x_I_{q}"] + variables[f"Bk_I_{q}"] == data["orders"][f"I_{q}"] + variables[f"Bk_I_{q-1}"])
            model.addConstr(variables[f"Iv_II_{q}"] - variables[f"x_II_{q}"] + variables[f"Bk_II_{q}"] == data["orders"][f"II_{q}"] + variables[f"Bk_II_{q-1}"])
            model.addConstr(variables[f"Iv_III_{q}"] - variables[f"x_III_{q}"] + variables[f"Bk_III_{q}"] == data["orders"][f"III_{q}"] + variables[f"Bk_III_{q-1}"])
    
    # Capacity constraints
    for q in data["quarters"]:
        model.addConstr(2 * variables[f"x_I_{q}"] + 4 * variables[f"x_II_{q}"] + 3 * variables[f"x_III_{q}"] <= data["capacity_hours_per_quarter"])
    
    # Ending inventory constraints
    for p in ["I", "II", "III"]:
        model.addConstr(variables[f"Iv_{p}_4"] == data["required_ending_inventory"])
    
    # Objective function
    obj = gp.quicksum([data["late_penalty_per_unit_per_quarter"]["I"] * variables[f"Bk_I_{q}"] for q in data["quarters"]]) + \
          gp.quicksum([data["late_penalty_per_unit_per_quarter"]["II"] * variables[f"Bk_II_{q}"] for q in data["quarters"]]) + \
          gp.quicksum([data["late_penalty_per_unit_per_quarter"]["III"] * variables[f"Bk_III_{q}"] for q in data["quarters"]]) + \
          gp.quicksum([data["storage_cost_per_unit_per_quarter"] * variables[f"Iv_I_{q}"] for q in data["quarters"]]) + \
          gp.quicksum([data["storage_cost_per_unit_per_quarter"] * variables[f"Iv_II_{q}"] for q in data["quarters"]]) + \
          gp.quicksum([data["storage_cost_per_unit_per_quarter"] * variables[f"Iv_III_{q}"] for q in data["quarters"]])
    
    model.setObjective(obj, gp.GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {
        "x_I_1": model.getVarByName("x_I_1").X,
        "x_I_2": model.getVarByName("x_I_2").X,
        "x_I_3": model.getVarByName("x_I_3").X,
        "x_I_4": model.getVarByName("x_I_4").X,
        "x_II_1": model.getVarByName("x_II_1").X,
        "x_II_2": model.getVarByName("x_II_2").X,
        "x_II_3": model.getVarByName("x_II_3").X,
        "x_II_4": model.getVarByName("x_II_4").X,
        "x_III_1": model.getVarByName("x_III_1").X,
        "x_III_2": model.getVarByName("x_III_2").X,
        "x_III_3": model.getVarByName("x_III_3").X,
        "x_III_4": model.getVarByName("x_III_4").X,
        "Iv_I_1": model.getVarByName("Iv_I_1").X,
        "Iv_I_2": model.getVarByName("Iv_I_2").X,
        "Iv_I_3": model.getVarByName("Iv_I_3").X,
        "Iv_I_4": model.getVarByName("Iv_I_4").X,
        "Iv_II_1": model.getVarByName("Iv_II_1").X,
        "Iv_II_2": model.getVarByName("Iv_II_2").X,
        "Iv_II_3": model.getVarByName("Iv_II_3").X,
        "Iv_II_4": model.getVarByName("Iv_II_4").X,
        "Iv_III_1": model.getVarByName("Iv_III_1").X,
        "Iv_III_2": model.getVarByName("Iv_III_2").X,
        "Iv_III_3": model.getVarByName("Iv_III_3").X,
        "Iv_III_4": model.getVarByName("Iv_III_4").X,
        "Bk_I_1": model.getVarByName("Bk_I_1").X,
        "Bk_I_2": model.getVarByName("Bk_I_2").X,
        "Bk_I_3": model.getVarByName("Bk_I_3").X,
        "Bk_I_4": model.getVarByName("Bk_I_4").X,
        "Bk_II_1": model.getVarByName("Bk_II_1").X,
        "Bk_II_2": model.getVarByName("Bk_II_2").X,
        "Bk_II_3": model.getVarByName("Bk_II_3").X,
        "Bk_II_4": model.getVarByName("Bk_II_4").X,
        "Bk_III_1": model.getVarByName("Bk_III_1").X,
        "Bk_III_2": model.getVarByName("Bk_III_2").X,
        "Bk_III_3": model.getVarByName("Bk_III_3").X,
        "Bk_III_4": model.getVarByName("Bk_III_4").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }