import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    
    # Decision variables: integer number of workers for each shift
    s1 = m.addVar(vtype=GRB.INTEGER, lb=0, name="s1")
    s2 = m.addVar(vtype=GRB.INTEGER, lb=0, name="s2")
    s3 = m.addVar(vtype=GRB.INTEGER, lb=0, name="s3")
    s4 = m.addVar(vtype=GRB.INTEGER, lb=0, name="s4")
    
    m.update()
    
    # Data extraction
    required = data["workers_required_by_window"]
    coverage = data["shift_coverage"]
    wages = data["shift_wage"]
    
    # Constraints: for each window w, sum of covering shifts >= required workers
    for w in range(len(required)):
        terms = []
        for k, var in (("1", s1), ("2", s2), ("3", s3), ("4", s4)):
            if w in coverage[k]:
                terms.append(var)
        m.addConstr(gp.quicksum(terms) >= required[w], name=f"cover_w{w}")
    
    # Objective: minimize total wage
    m.setObjective(
        s1 * wages["1"] + s2 * wages["2"] + s3 * wages["3"] + s4 * wages["4"],
        GRB.MINIMIZE
    )
    
    variables = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4
    }
    
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()
    
    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL"
    }
    status_str = status_map.get(status, str(status))
    objective = float(model.ObjVal) if model.ObjVal is not None else None
    
    solution = {k: float(v.X) for k, v in variables.items()}
    
    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }