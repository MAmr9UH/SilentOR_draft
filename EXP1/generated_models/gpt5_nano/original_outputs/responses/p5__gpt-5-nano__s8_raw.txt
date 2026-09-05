import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()
    
    # Create binary decision variables
    sel_calculus = model.addVar(vtype=gp.GRB.BINARY, name="sel_calculus")
    sel_or       = model.addVar(vtype=gp.GRB.BINARY, name="sel_or")
    sel_ds       = model.addVar(vtype=gp.GRB.BINARY, name="sel_ds")
    sel_bs       = model.addVar(vtype=gp.GRB.BINARY, name="sel_bs")
    sel_cs       = model.addVar(vtype=gp.GRB.BINARY, name="sel_cs")
    sel_cp       = model.addVar(vtype=gp.GRB.BINARY, name="sel_cp")
    sel_fc       = model.addVar(vtype=gp.GRB.BINARY, name="sel_fc")
    
    # Objective: minimize number of courses taken
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc, gp.GRB.MINIMIZE)
    
    # Constraints: category requirements
    model.addConstr(sel_calculus + sel_or + sel_ds + sel_bs + sel_fc >= 2, name="math_req")
    model.addConstr(sel_or + sel_bs + sel_cs + sel_fc >= 2, name="or_req")
    model.addConstr(sel_ds + sel_cs + sel_cp >= 2, name="comp_req")
    
    # Prerequisites
    # bs <= calculus
    model.addConstr(sel_bs <= sel_calculus, name="bs_prereq")
    # cs <= cp
    model.addConstr(sel_cs <= sel_cp, name="cs_prereq")
    # ds <= cp
    model.addConstr(sel_ds <= sel_cp, name="ds_prereq")
    # fc <= bs
    model.addConstr(sel_fc <= sel_bs, name="fc_prereq")
    
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
    
    # Map status to string
    status_code = getattr(model, "Status", None)
    status_str = "UNKNOWN"
    if status_code is not None:
        if status_code == gp.GRB.OPTIMAL:
            status_str = "OPTIMAL"
        elif status_code == gp.GRB.INFEASIBLE:
            status_str = "INFEASIBLE"
        elif status_code == gp.GRB.UNBOUNDED:
            status_str = "UNBOUNDED"
        elif status_code == gp.GRB.INF_OR_UNBD:
            status_str = "INF_OR_UNBD"
        elif status_code == gp.GRB.TIME_LIMIT:
            status_str = "TIME_LIMIT"
        elif status_code == gp.GRB.SUBOPTIMAL:
            status_str = "SUBOPTIMAL"
        elif status_code == gp.GRB.CUTOFF:
            status_str = "CUTOFF"
        else:
            status_str = str(status_code)
    
    obj_val = None
    try:
        obj_val = model.ObjVal
    except Exception:
        obj_val = None
    
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
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }