import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()
    
    # Days order is expected to be Monday ... Sunday
    days_order = data["days"]
    demands = data["demand"]
    
    # Explicit variable declarations for each possible start day
    start_Monday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Monday")
    start_Tuesday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Tuesday")
    start_Wednesday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Wednesday")
    start_Thursday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Thursday")
    start_Friday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Friday")
    start_Saturday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Saturday")
    start_Sunday = model.addVar(vtype=GRB.INTEGER, lb=0, name="start_Sunday")
    
    # Map day name to corresponding variable for easy access
    day_to_var = {
        "Monday": start_Monday,
        "Tuesday": start_Tuesday,
        "Wednesday": start_Wednesday,
        "Thursday": start_Thursday,
        "Friday": start_Friday,
        "Saturday": start_Saturday,
        "Sunday": start_Sunday
    }
    
    # Build coverage constraints: for each day d, sum of starts from days d, d-1, d-2, d-3, d-4 (mod 7) equals demand
    for i in range(7):
        # day_name for the current day
        current_day = days_order[i]
        demand = demands[current_day]
        # Sum starts from the five days that cover this day
        covering_days = [ days_order[(i - k) % 7] for k in range(5) ]
        constraint_expr = gp.quicksum(day_to_var[dd] for dd in covering_days)
        model.addConstr(constraint_expr == demand)
    
    # Objective: minimize total number of workers
    total_workers = gp.quicksum(day_to_var[day] for day in days_order)
    model.setObjective(total_workers, GRB.MINIMIZE)
    
    # Return model and the exact variables dict as required
    variables = {
        "start_Monday": start_Monday,
        "start_Tuesday": start_Tuesday,
        "start_Wednesday": start_Wednesday,
        "start_Thursday": start_Thursday,
        "start_Friday": start_Friday,
        "start_Saturday": start_Saturday,
        "start_Sunday": start_Sunday
    }
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)
    
    objective_val = float(model.ObjVal) if model.ObjVal is not None else None
    
    solution = {
        "start_Monday": int(variables["start_Monday"].X),
        "start_Tuesday": int(variables["start_Tuesday"].X),
        "start_Wednesday": int(variables["start_Wednesday"].X),
        "start_Thursday": int(variables["start_Thursday"].X),
        "start_Friday": int(variables["start_Friday"].X),
        "start_Saturday": int(variables["start_Saturday"].X),
        "start_Sunday": int(variables["start_Sunday"].X)
    }
    
    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }