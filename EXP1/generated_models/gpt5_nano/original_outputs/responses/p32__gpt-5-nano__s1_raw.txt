import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    batches = list(data["batches"])
    positions = list(data["positions"])
    vats = list(data["vats"])

    # Build time matrix t[i][j]
    t = {i: {j: 0.0 for j in vats} for i in batches}
    for i in batches:
        for j in vats:
            t[i][j] = data["processing_time"][str(i)][str(j)]

    model = gp.Model()

    # Decision variables
    y = model.addVars([(i, p) for i in batches for p in positions], vtype=GRB.BINARY, name="y")
    C = model.addVars([(p, j) for p in positions for j in vats], vtype=GRB.CONTINUOUS, lb=0.0, name="C")
    Cmax = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="Cmax")

    # Keep a convenient mapping for returning variables
    variables = {}

    for i in batches:
        for p in positions:
            key = f"y_{i}_{p}"
            variables[key] = y[i, p]

    for p in positions:
        for j in vats:
            key = f"C_{p}_{j}"
            variables[key] = C[p, j]

    variables["Cmax"] = Cmax

    # Sum-to-one constraints for permutation
    for i in batches:
        model.addConstr(quicksum(y[i, p] for p in positions) == 1, name=f"batch_assign_{i}")
    for p in positions:
        model.addConstr(quicksum(y[i, p] for i in batches) == 1, name=f"position_fill_{p}")

    # Completion time constraints
    # C_1_1 = sum_i t[i,1] * y_i_1
    model.addConstr(C[1, 1] == quicksum(t[i][1] * y[i, 1] for i in batches), name="C11_eq")

    # For vat 1, p > 1: C_p1 = C_{p-1,1} + sum_i t[i,1] * y_i_p
    for p in positions:
        if p == 1:
            continue
        model.addConstr(C[p, 1] == C[p - 1, 1] + quicksum(t[i][1] * y[i, p] for i in batches),
                        name=f"C{p}1_eq")

    # For vats 2 and 3
    for p in positions:
        for j in [2, 3]:
            t_sum = quicksum(t[i][j] * y[i, p] for i in batches)
            if p == 1:
                # C_1_j >= C_1_{j-1} + t_sum (since C_0_j = 0)
                model.addConstr(C[1, j] >= C[1, j - 1] + t_sum, name=f"C1{j}_ineq")
            else:
                # C_p_j >= C_{p-1}_j + t_sum
                model.addConstr(C[p, j] >= C[p - 1, j] + t_sum, name=f"C{p}{j}_down")
                # C_p_j >= C_p_{j-1} + t_sum
                model.addConstr(C[p, j] >= C[p, j - 1] + t_sum, name=f"C{p}{j}_across")

    # Makespan objective: minimize Cmax, with Cmax >= C_p3 for all p
    for p in positions:
        model.addConstr(Cmax >= C[p, 3], name=f"Cmax_ge_C{p}3")
    model.setObjective(Cmax, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    solution = {}

    # Extract solution values for y variables
    for i in data["batches"]:
        for p in data["positions"]:
            key = f"y_{i}_{p}"
            solution[key] = float(variables[key].X)

    # Extract C variables
    for p in data["positions"]:
        for j in data["vats"]:
            key = f"C_{p}_{j}"
            solution[key] = float(variables[key].X)

    # Cmax
    solution["Cmax"] = float(variables["Cmax"].X)

    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "minimum completion time of the last batch"},
            "solution": {
                "type": "object",
                "required": [
                    "y_1_1","y_1_2","y_1_3","y_1_4","y_1_5",
                    "y_2_1","y_2_2","y_2_3","y_2_4","y_2_5",
                    "y_3_1","y_3_2","y_3_3","y_3_4","y_3_5",
                    "y_4_1","y_4_2","y_4_3","y_4_4","y_4_5",
                    "y_5_1","y_5_2","y_5_3","y_5_4","y_5_5",
                    "C_1_1","C_1_2","C_1_3",
                    "C_2_1","C_2_2","C_2_3",
                    "C_3_1","C_3_2","C_3_3",
                    "C_4_1","C_4_2","C_4_3",
                    "C_5_1","C_5_2","C_5_3",
                    "Cmax"
                ],
                "properties": {str(k): {"type": "number"} for k in []}
            }
        }
    }

    objective_value = model.ObjVal if model.Status == GRB.OPTIMAL else None

    # Ensure numeric objective (could be None if not optimal)
    result["objective"] = objective_value

    # If objective is None due to no solve, still return solution values (could be defaults)
    result["status"] = status_str
    result["solution"] = solution

    return result