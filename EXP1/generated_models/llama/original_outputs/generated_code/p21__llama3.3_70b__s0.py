import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {
        "start_Monday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Monday"),
        "start_Tuesday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Tuesday"),
        "start_Wednesday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Wednesday"),
        "start_Thursday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Thursday"),
        "start_Friday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Friday"),
        "start_Saturday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Saturday"),
        "start_Sunday": model.addVar(vtype=gp.GRB.INTEGER, name="start_Sunday")
    }
    
    days = data["days"]
    demand = data["demand"]
    work_consecutive_days = data["work_consecutive_days"]
    off_consecutive_days = data["off_consecutive_days"]

    for i in range(len(days)):
        day = days[i]
        constraint = gp.LinExpr()
        for j in range(len(days)):
            if (i - j) % 7 >= 0 and (i - j) % 7 < work_consecutive_days:
                constraint.add(variables["start_" + days[j]])
        model.addConstr(constraint == demand[day], name=day)

    objective = gp.LinExpr()
    for var in variables.values():
        objective.add(var)
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
        "start_Monday": model.getVarByName("start_Monday").X,
        "start_Tuesday": model.getVarByName("start_Tuesday").X,
        "start_Wednesday": model.getVarByName("start_Wednesday").X,
        "start_Thursday": model.getVarByName("start_Thursday").X,
        "start_Friday": model.getVarByName("start_Friday").X,
        "start_Saturday": model.getVarByName("start_Saturday").X,
        "start_Sunday": model.getVarByName("start_Sunday").X
    }

    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }