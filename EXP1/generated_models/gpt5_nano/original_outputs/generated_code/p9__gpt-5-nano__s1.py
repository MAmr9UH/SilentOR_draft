from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi model for the employee scheduling problem.
    Returns (model, variables) where variables is a dict with keys "s0".."sN-1".
    """
    # Read instance data
    needs = data["employees_needed"]
    n = len(needs)
    w = int(data.get("work_days_consecutive", 5))

    # Create model
    model = Model()

    # Decision variables: s0..s_{n-1}
    s_vars = []
    for i in range(n):
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"s{i}")
        s_vars.append(v)
    model.update()

    # Constraints: For each day d, sum of starts from days d, d-1, ..., d-(w-1) >= needs[d]
    for d in range(n):
        involved = [ s_vars[(d - t) % n] for t in range(w) ]
        model.addConstr( quicksum(involved) >= needs[d], name=f"cover_day_{d}" )

    # Objective: minimize total number of starting workers
    model.setObjective( quicksum(s_vars), GRB.MINIMIZE )

    # Prepare variables dict to return
    variables = { f"s{i}": s_vars[i] for i in range(n) }

    return model, variables


def solve(data: dict) -> dict:
    """
    Solve the instance by building the model, optimizing, and returning the solution.
    The returned dict follows:
    {
      "status": "OPTIMAL" or other status string,
      "objective": <number>,
      "solution": {"s0": int, "s1": int, ..., "sn-1": int}
    }
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    obj_val = model.ObjVal

    # Read solution values
    sol = {}
    for i in range(len(variables)):
        val = variables[f"s{i}"].X
        if abs(val - round(val)) < 1e-6:
            sol[f"s{i}"] = int(round(val))
        else:
            sol[f"s{i}"] = float(val)

    return {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": sol
    }