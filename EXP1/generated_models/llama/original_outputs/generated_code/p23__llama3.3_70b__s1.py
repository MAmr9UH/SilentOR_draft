import gurobipy as gp

def solve(data):
    model = gp.Model()
    
    # Define variables
    w_vars = {}
    for i in range(6):
        for j in range(6):
            for k in range(6):
                var_name = f"w_{i}_{j}_{k}"
                w_vars[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Define objective function
    obj_func = gp.quicksum(
        (data["unit_price"]["1"] * data["spare_levels"][i]) +
        (data["unit_price"]["2"] * data["spare_levels"][j]) +
        (data["unit_price"]["3"] * data["spare_levels"][k])
        for i in range(6) for j in range(6) for k in range(6)
    )
    
    # Define constraints
    model.addConstr(gp.quicksum(w_vars.values()) == 1, name="one_combination")
    
    budget_constraint = gp.quicksum(
        (data["unit_price"]["1"] * data["spare_levels"][i] +
         data["unit_price"]["2"] * data["spare_levels"][j] +
         data["unit_price"]["3"] * data["spare_levels"][k]) *
        w_vars[f"w_{i}_{j}_{k}"]
        for i in range(6) for j in range(6) for k in range(6)
    )
    model.addConstr(budget_constraint <= data["budget"], name="budget")
    
    weight_constraint = gp.quicksum(
        (data["unit_weight"]["1"] * data["spare_levels"][i] +
         data["unit_weight"]["2"] * data["spare_levels"][j] +
         data["unit_weight"]["3"] * data["spare_levels"][k]) *
        w_vars[f"w_{i}_{j}_{k}"]
        for i in range(6) for j in range(6) for k in range(6)
    )
    model.addConstr(weight_constraint <= data["weight_limit"], name="weight")
    
    # Set objective function
    model.setObjective(obj_func, gp.GRB.MINIMIZE)
    
    # Optimize the model
    model.optimize()
    
    # Get solution status and value
    status = model.Status
    obj_val = model.ObjVal
    
    # Create variables dictionary with solution values
    variables = {var_name: var.X for var_name, var in w_vars.items()}
    
    return {
        "status": status,
        "obj_val": obj_val,
        "variables": variables
    }