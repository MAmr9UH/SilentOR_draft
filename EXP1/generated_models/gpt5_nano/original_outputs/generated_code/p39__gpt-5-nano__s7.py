import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    durations = data.get("durations", {})
    wcost = data.get("work_cost_per_project_day", 0)
    mcost = data.get("machine_rental_cost_per_day", 0)

    # Decision variables: starts
    start_A = model.addVar(lb=0.0, name="start_A", vtype=gp.GRB.CONTINUOUS)
    start_B = model.addVar(lb=0.0, name="start_B", vtype=gp.GRB.CONTINUOUS)
    start_C = model.addVar(lb=0.0, name="start_C", vtype=gp.GRB.CONTINUOUS)
    start_D = model.addVar(lb=0.0, name="start_D", vtype=gp.GRB.CONTINUOUS)
    start_E = model.addVar(lb=0.0, name="start_E", vtype=gp.GRB.CONTINUOUS)
    start_F = model.addVar(lb=0.0, name="start_F", vtype=gp.GRB.CONTINUOUS)
    start_G = model.addVar(lb=0.0, name="start_G", vtype=gp.GRB.CONTINUOUS)

    # Makespan and machine span
    Cmax = model.addVar(lb=0.0, name="Cmax", vtype=gp.GRB.CONTINUOUS)
    machine_span = model.addVar(lb=0.0, name="machine_span", vtype=gp.GRB.CONTINUOUS)

    # Helper maps
    start = {"A": start_A, "B": start_B, "C": start_C, "D": start_D, "E": start_E, "F": start_F, "G": start_G}

    # Precedence constraints: finish time of predecessor <= start time of successor
    for (pred, succ) in data.get("precedence", []):
        model.addConstr(start[succ] >= start[pred] + durations[pred])

    # Makespan constraints: Cmax must be >= finish times of all activities
    for act in ["A", "B", "C", "D", "E", "F", "G"]:
        model.addConstr(Cmax >= start[act] + durations[act])

    # Machine span = end of B - start of A
    machine_rental_from = data.get("machine_rental_from", "start_A")
    machine_rental_to = data.get("machine_rental_to", "end_B")

    # Generalized end time expression for "end_<Activity>"
    if machine_rental_to.startswith("end_"):
        end_act = machine_rental_to.split("_")[1]
        model.addConstr(machine_span == (start[end_act] + durations[end_act]) - start[machine_rental_from.split("_")[1]])
    else:
        # Fallback: treat as end_B if parsing fails
        model.addConstr(machine_span == (start["B"] + durations["B"]) - start[machine_rental_from.split("_")[1]])

    # Objective: minimize total cost
    objective = wcost * Cmax + mcost * machine_span
    model.setObjective(objective, gp.GRB.MINIMIZE)

    variables = {
        "start_A": start_A,
        "start_B": start_B,
        "start_C": start_C,
        "start_D": start_D,
        "start_E": start_E,
        "start_F": start_F,
        "start_G": start_G,
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_num = model.Status
    if status_num == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    model.update()
    objective_value = float(model.ObjVal)

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
        "objective": objective_value,
        "solution": solution
    }