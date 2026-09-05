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
    # Each container can hold at most 60 tons
    for i in data["container_ids"]:
        model.addConstr(
            gp.quicksum(data["weight_tons"][good] * variables[f"q_{i}_{good}"] for good in data["goods"]) 
            <= data["container_capacity_tons"] * variables[f"y_{i}"],
            name=f"capacity_{i}"
        )

    # Each used container must load at least 18 tons
    for i in data["container_ids"]:
        model.addConstr(
            gp.quicksum(data["weight_tons"][good] * variables[f"q_{i}_{good}"] for good in data["goods"]) 
            >= data["minimum_load_tons_if_used"] * variables[f"y_{i}"],
            name=f"min_load_{i}"
        )

    # Each used container must load at least 12 units of D
    for i in data["container_ids"]:
        model.addConstr(
            variables[f"q_{i}_D"] >= data["minimum_D_units_if_used"] * variables[f"y_{i}"],
            name=f"min_D_{i}"
        )

    # Whenever any A goods are loaded in a container, at least one unit of C must also be loaded
    for i in data["container_ids"]:
        model.addConstr(
            variables[f"uA_{i}"] <= variables[f"y_{i}"],
            name=f"A_requires_C_{i}_1"
        )
        model.addConstr(
            variables[f"q_{i}_A"] <= data["quantity"]["A"] * variables[f"uA_{i}"],
            name=f"A_requires_C_{i}_2"
        )
        model.addConstr(
            variables[f"q_{i}_C"] >= variables[f"uA_{i}"],
            name=f"A_requires_C_{i}_3"
        )

    # Total quantity of each good
    for good in data["goods"]:
        model.addConstr(
            gp.quicksum(variables[f"q_{i}_{good}"] for i in data["container_ids"]) == data["quantity"][good],
            name=f"total_quantity_{good}"
        )

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