import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build and return the Gurobi model and the dict of decision variables.
    The variables dict uses keys "s0".."s6" corresponding to workers starting on each day.
    """
    # Extract data
    demands = data["employees_needed"]
    n_days = len(demands)
    work_days_consecutive = data.get("work_days_consecutive", 5)

    model = gp.Model()

    # Create decision variables: s0..s6 (or s0..s{n_days-1} if generalized)
    variables = {}
    for i in range(n_days):
        key = f"s{i}"
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
        variables[key] = v

    # Objective: minimize total number of employees
    model.setObjective(gp.quicksum(variables[f"s{j}"] for j in range(n_days)), GRB.MINIMIZE)

    # Constraints: each day demand must be met by workers starting on that day or in the previous 4 days
    for d in range(n_days):
        covered = [(d - i) % n_days for i in range(work_days_consecutive)]
        expr = gp.quicksum(variables[f"s{idx}"] for idx in covered)
        model.addConstr(expr >= demands[d], name=f"day{d}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    """
    Solve the model built for the given data and return the solution in the required schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Prepare status string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    # Objective value
    objective = float(model.ObjVal)

    # Extract solution for s0..s6
    solution = {}
    for i in range(len(variables)):
        key = f"s{i}"
        solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }