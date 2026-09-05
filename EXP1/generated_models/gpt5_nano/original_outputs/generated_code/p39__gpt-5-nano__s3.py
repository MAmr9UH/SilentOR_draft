import gurobipy as gp

def build_model(data: dict):
    """
    Build and return a Gurobi model along with a dict of decision variables.
    """
    model = gp.Model()

    # Optional: silence solver output
    try:
        model.Params.OutputFlag = 0
    except Exception:
        pass

    dur = data["durations"]
    work_cost = data["work_cost_per_project_day"]
    rent_cost = data["machine_rental_cost_per_day"]

    # Decision variables: continuous start times, makespan, and machine span
    starts = {
        "A": model.addVar(lb=0.0, name="start_A"),
        "B": model.addVar(lb=0.0, name="start_B"),
        "C": model.addVar(lb=0.0, name="start_C"),
        "D": model.addVar(lb=0.0, name="start_D"),
        "E": model.addVar(lb=0.0, name="start_E"),
        "F": model.addVar(lb=0.0, name="start_F"),
        "G": model.addVar(lb=0.0, name="start_G"),
    }

    Cmax = model.addVar(lb=0.0, name="Cmax")
    machine_span = model.addVar(lb=0.0, name="machine_span")

    model.update()

    # Precedence constraints
    for (u, v) in data["precedence"]:
        model.addConstr(starts[v] >= starts[u] + dur[u])

    # Makespan constraints: Cmax >= start_i + dur[i] for all activities
    for k in ["A", "B", "C", "D", "E", "F", "G"]:
        model.addConstr(Cmax >= starts[k] + dur[k])

    # Machine span relation: machine_span = (end_B) - start_A
    model.addConstr(machine_span == (starts["B"] + dur["B"]) - starts["A"])

    # Objective: minimize total cost
    model.setObjective(work_cost * Cmax + rent_cost * machine_span, gp.GRB.MINIMIZE)

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
    """
    Build the model, solve it, and return the required solution dictionary.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(int(model.Status), str(int(model.Status)))
    obj_val = model.ObjVal if model.Status == gp.GRB.OPTIMAL else None

    # Read solution values
    model.update()
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

    result = {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": sol
    }

    return result