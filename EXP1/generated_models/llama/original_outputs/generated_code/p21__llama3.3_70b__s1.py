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

    for day in days:
        index = days.index(day)
        constraint = gp.quicksum([variables[day] for day in variables])
        for i in range(1, work_consecutive_days):
            next_index = (index + i) % len(days)
            constraint += variables[days[next_index]]
        model.addConstr(constraint >= demand[day], name=f"staffing_requirement_{day}")

    objective = gp.quicksum([variables[day] for day in variables])
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