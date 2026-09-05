import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Decision variables: integer number of workers for each shift
    s1 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s1")
    s2 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s2")
    s3 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s3")
    s4 = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name="s4")
    
    model.update()
    
    # Data
    demands = data["workers_required_by_window"]
    coverage = data["shift_coverage"]
    
    # Constraints: for each window, sum of the shifts covering that window >= demand
    for w in range(len(demands)):
        expr = gp.LinExpr()
        if w in coverage["1"]:
            expr += s1
        if w in coverage["2"]:
            expr += s2
        if w in coverage["3"]:
            expr += s3
        if w in coverage["4"]:
            expr += s4
        model.addConstr(expr >= demands[w], name=f"cover_w{w}")
    
    # Objective: minimize total wage
    model.setObjective(
        s1 * data["shift_wage"]["1"] +
        s2 * data["shift_wage"]["2"] +
        s3 * data["shift_wage"]["3"] +
        s4 * data["shift_wage"]["4"],
        gp.GRB.MINIMIZE
    )
    
    variables = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_int = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_int, str(status_int))
    
    objective = float(model.ObjVal)
    solution = {
        "s1": float(variables["s1"].X),
        "s2": float(variables["s2"].X),
        "s3": float(variables["s3"].X),
        "s4": float(variables["s4"].X)
    }
    
    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }