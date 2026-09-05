from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    regions = [1, 2, 3, 4, 5]
    
    # Read data
    current = {int(k): v for k, v in data["current_cars"].items()}
    needs = {int(k): v for k, v in data["cars_needed"].items()}
    move_cost = data["move_cost"]
    
    # Initialize model
    model = Model()
    
    # Decision variables: x_i_j for i != j
    variables = {}
    for i in regions:
        for j in regions:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
            variables[key] = v
    
    # Objective: minimize total moving cost
    objective = quicksum(move_cost[f"{i}_{j}"] * variables[f"x_{i}_{j}"]
                         for i in regions for j in regions if i != j)
    model.setObjective(objective, GRB.MINIMIZE)
    
    # Balance constraints: final cars in region r >= needs[r]
    for r in regions:
        incoming = quicksum(variables[f"x_{i}_{r}"] for i in regions if i != r)
        outgoing = quicksum(variables[f"x_{r}_{j}"] for j in regions if j != r)
        model.addConstr(current[r] + incoming - outgoing >= needs[r], name=f"bal_{r}")
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)
    
    # Read objective value
    obj_val = model.ObjVal
    
    # Ensure model is updated before reading variable values
    model.update()
    
    # Collect solution in required order
    ordered_keys = [
        "x_1_2", "x_1_3", "x_1_4", "x_1_5",
        "x_2_1", "x_2_3", "x_2_4", "x_2_5",
        "x_3_1", "x_3_2", "x_3_4", "x_3_5",
        "x_4_1", "x_4_2", "x_4_3", "x_4_5",
        "x_5_1", "x_5_2", "x_5_3", "x_5_4"
    ]
    solution = {}
    for key in ordered_keys:
        solution[key] = float(variables[key].X)
    
    return {
        "status": status,
        "objective": float(obj_val),
        "solution": solution
    }