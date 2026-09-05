import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "sel_calculus": model.addVar(vtype=gp.GRB.BINARY),
        "sel_or": model.addVar(vtype=gp.GRB.BINARY),
        "sel_ds": model.addVar(vtype=gp.GRB.BINARY),
        "sel_ms": model.addVar(vtype=gp.GRB.BINARY),
        "sel_cs": model.addVar(vtype=gp.GRB.BINARY),
        "sel_cp": model.addVar(vtype=gp.GRB.BINARY),
        "sel_fc": model.addVar(vtype=gp.GRB.BINARY)
    }
    
    # Objective: minimize the number of courses taken
    model.setObjective(gp.quicksum(variables.values()))
    
    # Constraints:
    # - Take at least two math courses
    model.addConstr(variables["sel_calculus"] + variables["sel_or"] + variables["sel_ds"] + variables["sel_ms"] + variables["sel_fc"] >= 2)
    
    # - Take at least two operations research courses
    model.addConstr(variables["sel_or"] + variables["sel_ms"] + variables["sel_cs"] + variables["sel_fc"] >= 2)
    
    # - Take at least two computer courses
    model.addConstr(variables["sel_ds"] + variables["sel_cs"] + variables["sel_cp"] >= 2)
    
    # Prerequisites:
    # - Computer simulation or data structures must be taken after computer programming
    model.addConstr(variables["sel_cs"] <= variables["sel_cp"])
    model.addConstr(variables["sel_ds"] <= variables["sel_cp"])
    
    # - Management statistics must be taken after calculus
    model.addConstr(variables["sel_ms"] <= variables["sel_calculus"])
    
    # - Forecasting must be taken after management statistics
    model.addConstr(variables["sel_fc"] <= variables["sel_ms"])
    
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
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": {
            "sel_calculus": variables["sel_calculus"].X,
            "sel_or": variables["sel_or"].X,
            "sel_ds": variables["sel_ds"].X,
            "sel_ms": variables["sel_ms"].X,
            "sel_cs": variables["sel_cs"].X,
            "sel_cp": variables["sel_cp"].X,
            "sel_fc": variables["sel_fc"].X
        }
    }