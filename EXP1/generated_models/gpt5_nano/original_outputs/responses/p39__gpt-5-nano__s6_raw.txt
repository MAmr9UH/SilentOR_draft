import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    durations = data["durations"]
    activities = data["activities"]
    w = data["work_cost_per_project_day"]
    m_cost = data["machine_rental_cost_per_day"]

    # Decision variables: starts for each activity, Cmax, and machine_span
    starts = {}
    for a in activities:
        starts[a] = model.addVar(lb=0.0, name=f"start_{a}", vtype=GRB.CONTINUOUS)

    Cmax = model.addVar(lb=0.0, name="Cmax", vtype=GRB.CONTINUOUS)
    machine_span = model.addVar(lb=0.0, name="machine_span", vtype=GRB.CONTINUOUS)

    # Objective: minimize total cost
    model.setObjective(w * Cmax + m_cost * machine_span, GRB.MINIMIZE)

    # Precedence constraints: start_i + duration_i <= start_j
    for (i, j) in data["precedence"]:
        model.addConstr(starts[i] + durations[i] <= starts[j], name=f"prec_{i}_{j}")

    # Makespan constraints: Cmax >= start_i + duration_i for all i
    for a in activities:
        model.addConstr(starts[a] + durations[a] <= Cmax, name=f"Cmax_{a}")

    # Machine rental span: machine_span = end_B - start_A = (start_B + dur_B) - start_A
    model.addConstr(machine_span == starts["B"] + durations["B"] - starts["A"], name="machine_span_def")

    variables = {
        "start_A": starts["A"],
        "start_B": starts["B"],
        "start_C": starts["C"],
        "start_D": starts["D"],
        "start_E": starts["E"],
        "start_F": starts["F"],
        "start_G": starts["G"],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    solution = {
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
        "solution": solution
    }