import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Unpack data
    students = data["students"]  # list of ints
    days = data["days"]          # list of strings e.g., ["Mon","Tue","Wed","Thu","Fri"]
    open_hours_per_day = data.get("open_hours_per_day", 14)
    max_students_per_day = data.get("max_students_per_day", 3)
    
    wages = {str(i): data["wage"][str(i)] for i in students}
    availability = data["availability_hours"]  # dict: str(i) -> dict(day -> hours)
    
    min_weekly_hours_undergrad = data.get("minimum_weekly_hours_undergrad", 8)
    min_weekly_hours_grad = data.get("minimum_weekly_hours_grad", 7)
    max_shifts_per_week = data.get("max_shifts_per_week", 2)
    undergraduates = set(data.get("undergraduates", []))
    graduates = set(data.get("graduates", []))
    
    # Create model
    model = gp.Model("LabDutyScheduling")
    model.Params.LogToConsole = 0  # keep quiet
    
    # Create variables
    variables = {}
    for i in students:
        for d in days:
            h_key = f"h_{i}_{d}"
            y_key = f"y_{i}_{d}"
            hv = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=h_key)
            yv = model.addVar(vtype=GRB.BINARY, name=y_key)
            variables[h_key] = hv
            variables[y_key] = yv
    model.update()
    
    # Constraints: daily coverage hours sum to open_hours_per_day
    for d in days:
        sum_h = gp.quicksum(variables[f"h_{i}_{d}"] for i in students)
        model.addConstr(sum_h == open_hours_per_day, name=f"cover_{d}")
        
        # Daily limit on number of students scheduled
        sum_y = gp.quicksum(variables[f"y_{i}_{d}"] for i in students)
        model.addConstr(sum_y <= max_students_per_day, name=f"max_students_{d}")
    
    # Link hours to availability and y (h_i_d <= availability * y_i_d)
    for i in students:
        for d in days:
            av = availability[str(i)].get(d, 0)
            model.addConstr(variables[f"h_{i}_{d}"] <= av * variables[f"y_{i}_{d}"])
    
    # Weekly minimum hours per student
    for i in students:
        total_hours_i = gp.quicksum(variables[f"h_{i}_{d}"] for d in days)
        if i in undergraduates:
            model.addConstr(total_hours_i >= min_weekly_hours_undergrad, name=f"min_hours_{i}")
        elif i in graduates:
            model.addConstr(total_hours_i >= min_weekly_hours_grad, name=f"min_hours_{i}")
        else:
            # If not categorized, apply undergraduate default
            model.addConstr(total_hours_i >= min_weekly_hours_undergrad, name=f"min_hours_{i}")
    
    # Weekly maximum shifts per student
    for i in students:
        sum_y_i = gp.quicksum(variables[f"y_{i}_{d}"] for d in days)
        model.addConstr(sum_y_i <= max_shifts_per_week, name=f"max_shifts_{i}")
    
    # Objective: minimize gross pay = sum_i,d wage_i * h_i_d
    obj = gp.quicksum(
        wages[str(i)] * variables[f"h_{i}_{d}"] for i in students for d in days
    )
    model.setObjective(obj, GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Status string mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))
    
    objective_value = float(model.ObjVal) if model.ObjVal is not None else float('nan')
    
    # Build solution dictionary with all h and y values
    solution = {}
    for i in data["students"]:
        for d in data["days"]:
            solution[f"h_{i}_{d}"] = float(variables[f"h_{i}_{d}"].X)
    for i in data["students"]:
        for d in data["days"]:
            solution[f"y_{i}_{d}"] = float(variables[f"y_{i}_{d}"].X)
    
    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }