import gurobipy as gp

def build_model(data: dict) -> tuple:
    # Build the Gurobi model for the employee scheduling problem
    m = gp.Model()
    m.Params.OutputFlag = 0  # suppress solver output

    days_needed = data["employees_needed"]
    work_days_consecutive = data.get("work_days_consecutive", 5)

    # Decision variables: s0..s6 = workers starting on each day
    s = [m.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"s{i}") for i in range(7)]

    # Objective: minimize total number of workers
    m.setObjective(gp.quicksum(s), gp.GRB.MINIMIZE)

    # Constraints: for each day d, the sum of workers starting on days d, d-1, ..., d-4 must meet the demand
    for d in range(7):
        coverage = gp.quicksum([s[(d - k) % 7] for k in range(work_days_consecutive)])
        m.addConstr(coverage >= days_needed[d])

    m.update()

    variables = {
        "variables_keys": {f"s{i}": s[i] for i in range(7)},
        "note": "Keys s0..s6 (workers starting each day, 0=Monday)."
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_str_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_str_map.get(status, str(status))

    obj_val = model.ObjVal
    objective = float(obj_val) if obj_val is not None else None

    solution = {}
    for i in range(7):
        solution[f"s{i}"] = int(variables["variables_keys"][f"s{i}"].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }