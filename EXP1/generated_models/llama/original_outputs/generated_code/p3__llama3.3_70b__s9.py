import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "s2": model.addVar(vtype=gp.GRB.INTEGER, name="s2"),
        "s6": model.addVar(vtype=gp.GRB.INTEGER, name="s6"),
        "s10": model.addVar(vtype=gp.GRB.INTEGER, name="s10"),
        "s14": model.addVar(vtype=gp.GRB.INTEGER, name="s14"),
        "s18": model.addVar(vtype=gp.GRB.INTEGER, name="s18"),
        "s22": model.addVar(vtype=gp.GRB.INTEGER, name="s22")
    }
    
    # Objective: minimize total number of salespeople
    model.setObjective(gp.quicksum(variables.values()), gp.GRB.MINIMIZE)
    
    # Constraints: meet demand in each period
    for i, period_start_time in enumerate(data["period_start_times"]):
        if i == 0:
            constraint = variables["s2"] + variables["s6"]
        elif i == 1:
            constraint = variables["s6"] + variables["s10"]
        elif i == 2:
            constraint = variables["s10"] + variables["s14"]
        elif i == 3:
            constraint = variables["s14"] + variables["s18"]
        elif i == 4:
            constraint = variables["s18"] + variables["s22"]
        else:
            constraint = variables["s22"] + variables["s2"]
        
        model.addConstr(constraint >= data["demand_by_period_start"][str(period_start_time)], name=f"meet_demand_{period_start_time}")
    
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
        "s2": model.getVarByName("s2").X,
        "s6": model.getVarByName("s6").X,
        "s10": model.getVarByName("s10").X,
        "s14": model.getVarByName("s14").X,
        "s18": model.getVarByName("s18").X,
        "s22": model.getVarByName("s22").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }