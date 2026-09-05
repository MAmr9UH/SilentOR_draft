from gurobipy import Model, GRB

def build_model(data: dict):
    model = Model("Basketweavers_University_Major")
    
    # Decision variables: 1 if the course is taken
    sel_calculus = model.addVar(vtype=GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=GRB.BINARY, name="sel_fc")
    
    model.update()
    
    # Objective: minimize total number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc, GRB.MINIMIZE)
    
    # Constraints: minimum requirements
    model.addConstr(sel_calculus + sel_or + sel_ds + sel_bs + sel_fc >= 2, name="math_ge2")  # Math requirement
    model.addConstr(sel_or + sel_bs + sel_cs + sel_fc >= 2, name="or_ge2")                 # OR requirement
    model.addConstr(sel_ds + sel_cs + sel_cp >= 2, name="comp_ge2")                       # Computer requirement
    
    # Prerequisites
    model.addConstr(sel_bs <= sel_calculus, name="prereq_bs_calculus")  # Calculus is prereq for BS
    model.addConstr(sel_ds <= sel_cp, name="prereq_ds_cp")              # cp prereq for DS
    model.addConstr(sel_cs <= sel_cp, name="prereq_cs_cp")              # cp prereq for CS
    model.addConstr(sel_fc <= sel_bs, name="prereq_fc_bs")              # BS prereq for FC
    
    variables = {
        "sel_calculus": sel_calculus,
        "sel_or": sel_or,
        "sel_ds": sel_ds,
        "sel_bs": sel_bs,
        "sel_cs": sel_cs,
        "sel_cp": sel_cp,
        "sel_fc": sel_fc
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_code, str(status_code))
    
    objective = float(model.ObjVal) if model.ObjVal is not None else 0.0
    
    solution = {
        "sel_calculus": int(variables["sel_calculus"].X),
        "sel_or": int(variables["sel_or"].X),
        "sel_ds": int(variables["sel_ds"].X),
        "sel_bs": int(variables["sel_bs"].X),
        "sel_cs": int(variables["sel_cs"].X),
        "sel_cp": int(variables["sel_cp"].X),
        "sel_fc": int(variables["sel_fc"].X)
    }
    
    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }