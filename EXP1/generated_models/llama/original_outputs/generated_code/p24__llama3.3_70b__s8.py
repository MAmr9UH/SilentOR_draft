import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    for i in data["container_ids"]:
        variables[f"y_{i}"] = model.addVar(vtype=gp.GRB.BINARY)
        variables[f"uA_{i}"] = model.addVar(vtype=gp.GRB.BINARY)
        for good in data["goods"]:
            variables[f"q_{i}_{good}"] = model.addVar(vtype=gp.GRB.INTEGER, lb=0)

    # Objective: minimize the number of used containers
    model.setObjective(gp.quicksum(variables[f"y_{i}"] for i in data["container_ids"]), gp.GRB.MINIMIZE)

    # Constraints:
    # Each good is packed completely
    for good in data["goods"]:
        model.addConstr(gp.quicksum(variables[f"q_{i}_{good}"] for i in data["container_ids"]) == data["quantity"][good])

    # Container capacity constraints
    for i in data["container_ids"]:
        model.addConstr(
            gp.quicksum(data["weight_tons"][good] * variables[f"q_{i}_{good}"] for good in data["goods"])
            <= data["container_capacity_tons"] * variables[f"y_{i}"]
        )

    # Minimum load constraints
    for i in data["container_ids"]:
        model.addConstr(
            gp.quicksum(data["weight_tons"][good] * variables[f"q_{i}_{good}"] for good in data["goods"])
            >= data["minimum_load_tons_if_used"] * variables[f"y_{i}"]
        )

    # Minimum D units constraints
    for i in data["container_ids"]:
        model.addConstr(variables[f"q_{i}_D"] >= data["minimum_D_units_if_used"] * variables[f"y_{i}"])

    # A requires at least one C in the same container
    if data["A_requires_at_least_one_C_in_same_container"]:
        for i in data["container_ids"]:
            model.addConstr(variables[f"q_{i}_C"] >= variables[f"uA_{i}"])
            model.addConstr(variables[f"q_{i}_A"] <= 1000 * variables[f"uA_{i}"])  # big M
            model.addConstr(variables[f"q_{i}_A"] >= variables[f"uA_{i}"])

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {key: variables[key].X for key in variables}
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }