import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {
        "s2": model.addVar(vtype=gp.GRB.INTEGER),
        "s6": model.addVar(vtype=gp.GRB.INTEGER),
        "s10": model.addVar(vtype=gp.GRB.INTEGER),
        "s14": model.addVar(vtype=gp.GRB.INTEGER),
        "s18": model.addVar(vtype=gp.GRB.INTEGER),
        "s22": model.addVar(vtype=gp.GRB.INTEGER)
    }
    
    # Constraints for each period
    model.addConstr(variables["s2"] + variables["s6"] >= data["demand_by_period_start"]["2"])
    model.addConstr(variables["s6"] + variables["s10"] >= data["demand_by_period_start"]["6"])
    model.addConstr(variables["s10"] + variables["s14"] >= data["demand_by_period_start"]["10"])
    model.addConstr(variables["s14"] + variables["s18"] >= data["demand_by_period_start"]["14"])
    model.addConstr(variables["s18"] + variables["s22"] >= data["demand_by_period_start"]["18"])
    model.addConstr(variables["s2"] + variables["s22"] >= data["demand_by_period_start"]["22"])

    # Objective: minimize total number of salespeople
    model.setObjective(gp.quicksum(list(variables.values())))

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