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
        window_coverage = gp.quicksum([variables[f"s{j}"] for j in data["shifts"] if i in data["shift_coverage"][str(j)]])
        model.addConstr(window_coverage >= data["workers_required_by_window"][i], name=f"window_{i}")
    
    objective = gp.quicksum([data["shift_wage"][str(i+1)] * variables[f"s{i+1}"] for i in range(len(data["shifts"]))])
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
        "s1": _.get("s1").X,
        "s2": _.get("s2").X,
        "s3": _.get("s3").X,
        "s4": _.get("s4").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }