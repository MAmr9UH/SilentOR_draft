import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {
        "s1": model.addVar(vtype=gp.GRB.INTEGER, name="s1"),
        "s2": model.addVar(vtype=gp.GRB.INTEGER, name="s2"),
        "s3": model.addVar(vtype=gp.GRB.INTEGER, name="s3"),
        "s4": model.addVar(vtype=gp.GRB.INTEGER, name="s4")
    }
    
    for i in range(len(data["time_windows"])):
        window_coverage = gp.quicksum([variables["s1"] if 0 <= i <= 2 else 0,
                                        variables["s2"] if 2 <= i <= 4 else 0,
                                        variables["s3"] if 4 <= i <= 6 else 0,
                                        variables["s4"] if (i == 7 or i == 0) else 0])
        model.addConstr(window_coverage >= data["workers_required_by_window"][i], name=f"window_{i}")
    
    objective = gp.quicksum([variables["s1"] * data["shift_wage"]["1"],
                             variables["s2"] * data["shift_wage"]["2"],
                             variables["s3"] * data["shift_wage"]["3"],
                             variables["s4"] * data["shift_wage"]["4"]])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
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
        "s1": model.getVarByName("s1").X,
        "s2": model.getVarByName("s2").X,
        "s3": model.getVarByName("s3").X,
        "s4": model.getVarByName("s4").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }