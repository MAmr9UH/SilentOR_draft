import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    warehouses = data.get("warehouses", [])
    truck_contents = data.get("truck_contents", {})
    freight_cost = data.get("freight_cost", {})
    raw_materials = data.get("raw_materials", [])
    
    # Required amounts for each material (read from problem instance)
    required = {'A': 240, 'B': 80, 'C': 120}
    
    # Decision variables: number of trucks dispatched from each warehouse
    trucks = {}
    for w in warehouses:
        trucks[w] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"trucks_{w}")
    
    # Objective: minimize total freight cost
    model.setObjective(gp.quicksum(freight_cost[w] * trucks[w] for w in warehouses), GRB.MINIMIZE)
    
    # Constraints: meet material requirements
    for m in raw_materials:
        model.addConstr(gp.quicksum(truck_contents[w][m] * trucks[w] for w in warehouses) >= required[m], name=f"req_{m}")
    
    return model, {'trucks_A': trucks.get('A'), 'trucks_B': trucks.get('B')}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))
    
    objective = float(model.ObjVal)
    
    sol_A = int(variables['trucks_A'].X) if variables.get('trucks_A') is not None else None
    sol_B = int(variables['trucks_B'].X) if variables.get('trucks_B') is not None else None
    
    solution = {
        "trucks_A": sol_A,
        "trucks_B": sol_B
    }
    
    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }