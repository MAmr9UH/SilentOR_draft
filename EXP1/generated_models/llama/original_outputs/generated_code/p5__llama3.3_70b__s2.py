import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "sel_calculus": model.addVar(vtype=gp.GRB.BINARY),
        "sel_or": model.addVar(vtype=gp.GRB.BINARY),
        "sel_ds": model.addVar(vtype=gp.GRB.BINARY),
        "sel_bs": model.addVar(vtype=gp.GRB.BINARY),
        "sel_cs": model.addVar(vtype=gp.GRB.BINARY),
        "sel_cp": model.addVar(vtype=gp.GRB.BINARY),
        "sel_fc": model.addVar(vtype=gp.GRB.BINARY)
    }
    
    # Math requirement
    model.addConstr(variables["sel_calculus"] + variables["sel_or"] + variables["sel_ds"] + variables["sel_bs"] + variables["sel_fc"] >= 2)
    
    # OR requirement
    model.addConstr(variables["sel_or"] + variables["sel_bs"] + variables["sel_cs"] + variables["sel_fc"] >= 2)
    
    # Computer requirement
    model.addConstr(variables["sel_ds"] + variables["sel_cs"] + variables["sel_cp"] >= 2)
    
    # Prerequisites
    model.addConstr(variables["sel_bs"] <= variables["sel_calculus"])
    model.addConstr(variables["sel_cs"] <= variables["sel_cp"])
    model.addConstr(variables["sel_ds"] <= variables["sel_cp"])
    model.addConstr(variables["sel_fc"] <= variables["sel_bs"])
    
    # Objective
    model.setObjective(gp.quicksum([variables[var] for var in variables]), gp.GRB.MINIMIZE)
    
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
        "sel_calculus": variables["sel_calculus"].X,
        "sel_or": variables["sel_or"].X,
        "sel_ds": variables["sel_ds"].X,
        "sel_bs": variables["sel_bs"].X,
        "sel_cs": variables["sel_cs"].X,
        "sel_cp": variables["sel_cp"].X,
        "sel_fc": variables["sel_fc"].X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }