import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    
    # Decision variables: number of trucks from A and B
    trucks_A = m.addVar(vtype=GRB.INTEGER, name="trucks_A", lb=0)
    trucks_B = m.addVar(vtype=GRB.INTEGER, name="trucks_B", lb=0)
    
    # Read data
    contents = data.get("truck_contents", {})
    freight = data.get("freight_cost", {})
    
    A_contents = contents.get("A", {})
    B_contents = contents.get("B", {})
    
    aA = A_contents.get("A", 0)  # pieces of A per A-truck
    aB = A_contents.get("B", 0)  # kg of B per A-truck
    aC = A_contents.get("C", 0)  # tons of C per A-truck
    
    bA = B_contents.get("A", 0)  # pieces of A per B-truck
    bB = B_contents.get("B", 0)  # kg of B per B-truck
    bC = B_contents.get("C", 0)  # tons of C per B-truck
    
    need_A = 240
    need_B = 80
    need_C = 120
    
    # Constraints: meet minimum requirements
    m.addConstr(aA * trucks_A + bA * trucks_B >= need_A, name="need_A")
    m.addConstr(aB * trucks_A + bB * trucks_B >= need_B, name="need_B")
    m.addConstr(aC * trucks_A + bC * trucks_B >= need_C, name="need_C")
    
    # Objective: minimize total freight cost
    m.setObjective(freight.get("A", 0) * trucks_A + freight.get("B", 0) * trucks_B, GRB.MINIMIZE)
    
    m.update()
    
    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }
    
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()
    
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
    
    obj_val = model.ObjVal
    trucks_A_val = int(round(variables["trucks_A"].X))
    trucks_B_val = int(round(variables["trucks_B"].X))
    
    solution = {
        "trucks_A": trucks_A_val,
        "trucks_B": trucks_B_val
    }
    
    return {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else 0.0,
        "solution": solution
    }