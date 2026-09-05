import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    activities = data["activities"]
    durations = data["durations"]
    precedences = data["precedence"]
    work_cost = data["work_cost_per_project_day"]
    machine_cost = data["machine_rental_cost_per_day"]

    model = gp.Model()

    # Decision variables: start times
    start = {act: model.addVar(lb=0.0, name=f"start_{act}", vtype=GRB.CONTINUOUS) for act in activities}
    Cmax = model.addVar(lb=0.0, name="Cmax", vtype=GRB.CONTINUOUS)
    machine_span = model.addVar(lb=0.0, name="machine_span", vtype=GRB.CONTINUOUS)

    # Collect variables in the required dict format
    variables = {
        "start_A": start["A"],
        "start_B": start["B"],
        "start_C": start["C"],
        "start_D": start["D"],
        "start_E": start["E"],
        "start_F": start["F"],
        "start_G": start["G"],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    # Precedence constraints: finish(i) <= start(j)
    for (i, j) in precedences:
        model.addConstr(start[j] >= start[i] + durations[i], name=f"prec_{i}_{j}")

    # Cmax constraints: Cmax >= finish_i for all i
    for act in activities:
        model.addConstr(Cmax >= start[act] + durations[act], name=f"completes_{act}")

    # Machine span definition: machine_span = end_B - start_A
    model.addConstr(machine_span == (start["B"] + durations["B"]) - start["A"], name="machine_span_def")

    # Objective: minimize total cost
    model.setObjective(work_cost * Cmax + machine_cost * machine_span, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INTERRUPTED: "INTERRUPTED",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    objective = None
    if model.Status == GRB.OPTIMAL or model.Status == GRB.SUBOPTIMAL:
        objective = float(model.ObjVal)
    else:
        objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values
    sol = {
        "start_A": float(variables["start_A"].X),
        "start_B": float(variables["start_B"].X),
        "start_C": float(variables["start_C"].X),
        "start_D": float(variables["start_D"].X),
        "start_E": float(variables["start_E"].X),
        "start_F": float(variables["start_F"].X),
        "start_G": float(variables["start_G"].X),
        "Cmax": float(variables["Cmax"].X),
        "machine_span": float(variables["machine_span"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": sol
    }