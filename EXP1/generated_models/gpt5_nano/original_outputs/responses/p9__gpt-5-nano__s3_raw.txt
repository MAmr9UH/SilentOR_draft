import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Create decision variables: s0..s6
    variables = {}
    for i in range(7):
        variables[f's{i}'] = model.addVar(vtype=GRB.INTEGER, lb=0, name=f's{i}')

    # Read data
    needs = data["employees_needed"]
    # Add constraints: for each day d, sum of workers starting on days d, d-1, ..., d-4 >= needs[d]
    for d in range(7):
        involved = [ variables[f's{(d - i) % 7}'] for i in range(5) ]
        model.addConstr( quicksum(involved) >= needs[d], name=f'cover_day_{d}' )

    # Objective: minimize total number of workers
    model.setObjective( quicksum( variables[f's{i}'] for i in range(7) ), GRB.MINIMIZE )

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal)

    solution = { f's{i}': int(variables[f's{i}'].X) for i in range(7) }

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }