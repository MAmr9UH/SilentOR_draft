import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "y_c1": model.addVar(vtype=gp.GRB.BINARY),
        "y_c2": model.addVar(vtype=gp.GRB.BINARY),
        "y_c3": model.addVar(vtype=gp.GRB.BINARY),
        "y_c4": model.addVar(vtype=gp.GRB.BINARY),
        "f_c1_s1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s5": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s6": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c1_s8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s5": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s6": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c2_s8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s5": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s6": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c3_s8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s5": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s6": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "f_c4_s8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    }
    
    # Objective function
    obj = gp.quicksum([data["fixed_opening_cost"]["c1"] * variables["y_c1"],
                       data["fixed_opening_cost"]["c2"] * variables["y_c2"],
                       data["fixed_opening_cost"]["c3"] * variables["y_c3"],
                       data["fixed_opening_cost"]["c4"] * variables["y_c4"],
                       data["transport_cost"]["c1"]["s1"] * variables["f_c1_s1"],
                       data["transport_cost"]["c1"]["s2"] * variables["f_c1_s2"],
                       data["transport_cost"]["c1"]["s3"] * variables["f_c1_s3"],
                       data["transport_cost"]["c1"]["s4"] * variables["f_c1_s4"],
                       data["transport_cost"]["c1"]["s5"] * variables["f_c1_s5"],
                       data["transport_cost"]["c1"]["s6"] * variables["f_c1_s6"],
                       data["transport_cost"]["c1"]["s7"] * variables["f_c1_s7"],
                       data["transport_cost"]["c1"]["s8"] * variables["f_c1_s8"],
                       data["transport_cost"]["c2"]["s1"] * variables["f_c2_s1"],
                       data["transport_cost"]["c2"]["s2"] * variables["f_c2_s2"],
                       data["transport_cost"]["c2"]["s3"] * variables["f_c2_s3"],
                       data["transport_cost"]["c2"]["s4"] * variables["f_c2_s4"],
                       data["transport_cost"]["c2"]["s5"] * variables["f_c2_s5"],
                       data["transport_cost"]["c2"]["s6"] * variables["f_c2_s6"],
                       data["transport_cost"]["c2"]["s7"] * variables["f_c2_s7"],
                       data["transport_cost"]["c2"]["s8"] * variables["f_c2_s8"],
                       data["transport_cost"]["c3"]["s1"] * variables["f_c3_s1"],
                       data["transport_cost"]["c3"]["s2"] * variables["f_c3_s2"],
                       data["transport_cost"]["c3"]["s3"] * variables["f_c3_s3"],
                       data["transport_cost"]["c3"]["s4"] * variables["f_c3_s4"],
                       data["transport_cost"]["c3"]["s5"] * variables["f_c3_s5"],
                       data["transport_cost"]["c3"]["s6"] * variables["f_c3_s6"],
                       data["transport_cost"]["c3"]["s7"] * variables["f_c3_s7"],
                       data["transport_cost"]["c3"]["s8"] * variables["f_c3_s8"],
                       data["transport_cost"]["c4"]["s1"] * variables["f_c4_s1"],
                       data["transport_cost"]["c4"]["s2"] * variables["f_c4_s2"],
                       data["transport_cost"]["c4"]["s3"] * variables["f_c4_s3"],
                       data["transport_cost"]["c4"]["s4"] * variables["f_c4_s4"],
                       data["transport_cost"]["c4"]["s5"] * variables["f_c4_s5"],
                       data["transport_cost"]["c4"]["s6"] * variables["f_c4_s6"],
                       data["transport_cost"]["c4"]["s7"] * variables["f_c4_s7"],
                       data["transport_cost"]["c4"]["s8"] * variables["f_c4_s8"]])
    model.setObjective(obj, gp.GRB.MINIMIZE)
    
    # Constraints
    model.addConstr(variables["f_c1_s1"] + variables["f_c2_s1"] + variables["f_c3_s1"] + variables["f_c4_s1"] == data["demand"]["s1"])
    model.addConstr(variables["f_c1_s2"] + variables["f_c2_s2"] + variables["f_c3_s2"] + variables["f_c4_s2"] == data["demand"]["s2"])
    model.addConstr(variables["f_c1_s3"] + variables["f_c2_s3"] + variables["f_c3_s3"] + variables["f_c4_s3"] == data["demand"]["s3"])
    model.addConstr(variables["f_c1_s4"] + variables["f_c2_s4"] + variables["f_c3_s4"] + variables["f_c4_s4"] == data["demand"]["s4"])
    model.addConstr(variables["f_c1_s5"] + variables["f_c2_s5"] + variables["f_c3_s5"] + variables["f_c4_s5"] == data["demand"]["s5"])
    model.addConstr(variables["f_c1_s6"] + variables["f_c2_s6"] + variables["f_c3_s6"] + variables["f_c4_s6"] == data["demand"]["s6"])
    model.addConstr(variables["f_c1_s7"] + variables["f_c2_s7"] + variables["f_c3_s7"] + variables["f_c4_s7"] == data["demand"]["s7"])
    model.addConstr(variables["f_c1_s8"] + variables["f_c2_s8"] + variables["f_c3_s8"] + variables["f_c4_s8"] == data["demand"]["s8"])
    
    model.addConstr(variables["f_c1_s1"] + variables["f_c1_s2"] + variables["f_c1_s3"] + variables["f_c1_s4"] +
                     variables["f_c1_s5"] + variables["f_c1_s6"] + variables["f_c1_s7"] + variables["f_c1_s8"] <= data["capacity"]["c1"])
    model.addConstr(variables["f_c2_s1"] + variables["f_c2_s2"] + variables["f_c2_s3"] + variables["f_c2_s4"] +
                     variables["f_c2_s5"] + variables["f_c2_s6"] + variables["f_c2_s7"] + variables["f_c2_s8"] <= data["capacity"]["c2"])
    model.addConstr(variables["f_c3_s1"] + variables["f_c3_s2"] + variables["f_c3_s3"] + variables["f_c3_s4"] +
                     variables["f_c3_s5"] + variables["f_c3_s6"] + variables["f_c3_s7"] + variables["f_c3_s8"] <= data["capacity"]["c3"])
    model.addConstr(variables["f_c4_s1"] + variables["f_c4_s2"] + variables["f_c4_s3"] + variables["f_c4_s4"] +
                     variables["f_c4_s5"] + variables["f_c4_s6"] + variables["f_c4_s7"] + variables["f_c4_s8"] <= data["capacity"]["c4"])
    
    model.addConstr(variables["f_c1_s1"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s2"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s3"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s4"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s5"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s6"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s7"] <= variables["y_c1"])
    model.addConstr(variables["f_c1_s8"] <= variables["y_c1"])
    
    model.addConstr(variables["f_c2_s1"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s2"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s3"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s4"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s5"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s6"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s7"] <= variables["y_c2"])
    model.addConstr(variables["f_c2_s8"] <= variables["y_c2"])
    
    model.addConstr(variables["f_c3_s1"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s2"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s3"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s4"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s5"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s6"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s7"] <= variables["y_c3"])
    model.addConstr(variables["f_c3_s8"] <= variables["y_c3"])
    
    model.addConstr(variables["f_c4_s1"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s2"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s3"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s4"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s5"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s6"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s7"] <= variables["y_c4"])
    model.addConstr(variables["f_c4_s8"] <= variables["y_c4"])
    
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
    
    solution = {
        "y_c1": variables["y_c1"].X,
        "y_c2": variables["y_c2"].X,
        "y_c3": variables["y_c3"].X,
        "y_c4": variables["y_c4"].X,
        "f_c1_s1": variables["f_c1_s1"].X,
        "f_c1_s2": variables["f_c1_s2"].X,
        "f_c1_s3": variables["f_c1_s3"].X,
        "f_c1_s4": variables["f_c1_s4"].X,
        "f_c1_s5": variables["f_c1_s5"].X,
        "f_c1_s6": variables["f_c1_s6"].X,
        "f_c1_s7": variables["f_c1_s7"].X,
        "f_c1_s8": variables["f_c1_s8"].X,
        "f_c2_s1": variables["f_c2_s1"].X,
        "f_c2_s2": variables["f_c2_s2"].X,
        "f_c2_s3": variables["f_c2_s3"].X,
        "f_c2_s4": variables["f_c2_s4"].X,
        "f_c2_s5": variables["f_c2_s5"].X,
        "f_c2_s6": variables["f_c2_s6"].X,
        "f_c2_s7": variables["f_c2_s7"].X,
        "f_c2_s8": variables["f_c2_s8"].X,
        "f_c3_s1": variables["f_c3_s1"].X,
        "f_c3_s2": variables["f_c3_s2"].X,
        "f_c3_s3": variables["f_c3_s3"].X,
        "f_c3_s4": variables["f_c3_s4"].X,
        "f_c3_s5": variables["f_c3_s5"].X,
        "f_c3_s6": variables["f_c3_s6"].X,
        "f_c3_s7": variables["f_c3_s7"].X,
        "f_c3_s8": variables["f_c3_s8"].X,
        "f_c4_s1": variables["f_c4_s1"].X,
        "f_c4_s2": variables["f_c4_s2"].X,
        "f_c4_s3": variables["f_c4_s3"].X,
        "f_c4_s4": variables["f_c4_s4"].X,
        "f_c4_s5": variables["f_c4_s5"].X,
        "f_c4_s6": variables["f_c4_s6"].X,
        "f_c4_s7": variables["f_c4_s7"].X,
        "f_c4_s8": variables["f_c4_s8"].X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }