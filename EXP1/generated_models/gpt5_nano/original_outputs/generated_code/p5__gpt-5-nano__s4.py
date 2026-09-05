import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()

    # Decision variables: binary indicators for taking each course
    sel_calculus = model.addVar(vtype=gp.GRB.BINARY, name="sel_calculus")
    sel_or = model.addVar(vtype=gp.GRB.BINARY, name="sel_or")
    sel_ds = model.addVar(vtype=gp.GRB.BINARY, name="sel_ds")
    sel_bs = model.addVar(vtype=gp.GRB.BINARY, name="sel_bs")
    sel_cs = model.addVar(vtype=gp.GRB.BINARY, name="sel_cs")
    sel_cp = model.addVar(vtype=gp.GRB.BINARY, name="sel_cp")
    sel_fc = model.addVar(vtype=gp.GRB.BINARY, name="sel_fc")

    # Prerequisites
    # bs requires calculus
    model.addConstr(sel_bs <= sel_calculus, name="prereq_bs_calculus")
    # fc requires bs
    model.addConstr(sel_fc <= sel_bs, name="prereq_fc_bs")
    # ds requires cp
    model.addConstr(sel_ds <= sel_cp, name="prereq_ds_cp")
    # cs requires cp
    model.addConstr(sel_cs <= sel_cp, name="prereq_cs_cp")

    # Major requirements
    # Math: calculus, ds, bs, fc -> at least 2
    math_courses = sel_calculus + sel_ds + sel_bs + sel_fc
    model.addConstr(math_courses >= 2, name="math_req")

    # OR: or, bs, cs, fc -> at least 2
    or_courses = sel_or + sel_bs + sel_cs + sel_fc
    model.addConstr(or_courses >= 2, name="or_req")

    # Computer: ds, cs, cp -> at least 2
    comp_courses = sel_ds + sel_cs + sel_cp
    model.addConstr(comp_courses >= 2, name="computer_req")

    # Objective: minimize number of courses
    model.setObjective(sel_calculus + sel_or + sel_ds + sel_bs + sel_cs + sel_cp + sel_fc, gp.GRB.MINIMIZE)

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
    # Ensure up-to-date variable values
    model.update()

    status = model.Status
    # Map status to a readable string where possible
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status_str = status_map.get(status, str(status))

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

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
        "objective": objective_value,
        "solution": solution
    }