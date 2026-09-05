import gurobipy as gp

def solve(data):
    model = gp.Model()
    
    # Define variables
    w_vars = {}
    for i in range(len(data['components'])):
        for j in range(len(data['spare_levels'])):
            for k in range(len(data['spare_levels'])):
                if len(data['components']) == 3 and len(data['spare_levels']) == 6:
                    var_name = f"w_{i+1}_{j}_{k}"
                    w_vars[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Define objective function
    obj_func = gp.quicksum(
        -data['reliability'][str(i+1)][j] * data['unit_price'][str(i+1)] * w_vars[f"w_{i+1}_{j}_{k}"]
        for i in range(len(data['components']))
        for j in range(len(data['spare_levels']))
        for k in range(len(data['spare_levels']))
    )
    
    # Define constraints
    model.addConstr(gp.quicksum(w_vars.values()) == 1, name="one_combination")
    model.addConstr(
        gp.quicksum(
            data['unit_price'][str(i+1)] * w_vars[f"w_{i+1}_{j}_{k}"]
            for i in range(len(data['components']))
            for j in range(len(data['spare_levels']))
            for k in range(len(data['spare_levels']))
        ) <= data['budget'], name="budget_constraint"
    )
    model.addConstr(
        gp.quicksum(
            data['unit_weight'][str(i+1)] * w_vars[f"w_{i+1}_{j}_{k}"]
            for i in range(len(data['components']))
            for j in range(len(data['spare_levels']))
            for k in range(len(data['spare_levels']))
        ) <= data['weight_limit'], name="weight_constraint"
    )
    
    # Set objective function
    model.setObjective(obj_func, gp.GRB.MAXIMIZE)
    
    # Optimize the model
    model.optimize()
    
    # Get solution status and value
    status = model.Status
    obj_val = model.ObjVal
    
    # Get variable values
    variables = {var_name: var.X for var_name, var in w_vars.items()}
    
    return {
        'status': status,
        'obj_val': obj_val,
        'variables': variables
    }

# Call the function with data
data = {
  "components": [
    1,
    2,
    3
  ],
  "spare_levels": [
    0,
    1,
    2,
    3,
    4,
    5
  ],
  "reliability": {
    "1": [
      0.5,
      0.6,
      0.7,
      0.8,
      0.9,
      1.0
    ],
    "2": [
      0.6,
      0.75,
      0.95,
      1.0,
      1.0,
      1.0
    ],
    "3": [
      0.7,
      0.9,
      1.0,
      1.0,
      1.0,
      1.0
    ]
  },
  "unit_price": {
    "1": 20,
    "2": 30,
    "3": 40
  },
  "unit_weight": {
    "1": 2,
    "2": 4,
    "3": 6
  },
  "budget": 150,
  "weight_limit": 20,
}

result = solve(data)