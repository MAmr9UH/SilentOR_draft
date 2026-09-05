import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi model for the staffing problem.
    Returns:
        model, variables
    """
    m = gp.Model()
    days = data["days"]
    demand = data["demand"]
    work_len = int(data.get("work_consecutive_days", 5))

    # Create exactly the seven integer decision variables
    var_names = [
        "start_Monday",
        "start_Tuesday",
        "start_Wednesday",
        "start_Thursday",
        "start_Friday",
        "start_Saturday",
        "start_Sunday",
    ]
    starts = {}
    for name in var_names:
        starts[name] = m.addVar(vtype=GRB.INTEGER, lb=0, name=name)
    m.update()

    # Build the coverage constraints: for each day i, sum of starts over the
    # last `work_len` days (mod 7) must meet the demand on day i.
    starts_list = [starts[n] for n in var_names]
    for i, day in enumerate(days):
        expr = gp.quicksum(starts_list[(i - k) % 7] for k in range(work_len))
        m.addConstr(expr >= demand[day])

    m.update()
    return m, starts

def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the solution in the requested schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = int(model.Status)
    def status_to_name(code: int) -> str:
        mapping = {
            GRB.OPTIMAL: "OPTIMAL",
            GRB.INFEASIBLE: "INFEASIBLE",
            GRB.UNBOUNDED: "UNBOUNDED",
            GRB.TIME_LIMIT: "TIME_LIMIT",
            GRB.SUBOPTIMAL: "SUBOPTIMAL",
            GRB.INF_OR_UNBD: "INF_OR_UNBD",
        }
        return mapping.get(code, str(code))

    status_str = status_to_name(status_code)

    model.update()
    objective = float(model.ObjVal)

    # Extract solution values for each variable
    solution = {}
    order = [
        "start_Monday",
        "start_Tuesday",
        "start_Wednesday",
        "start_Thursday",
        "start_Friday",
        "start_Saturday",
        "start_Sunday",
    ]
    for key in order:
        val = variables[key].X
        if abs(val - round(val)) < 1e-6:
            solution[key] = int(round(val))
        else:
            solution[key] = float(val)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }