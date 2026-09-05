import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    trucks_A = model.addVar(vtype=gp.GRB.INTEGER, name="trucks_A")
    trucks_B = model.addVar(vtype=gp.GRB.INTEGER, name="trucks_B")

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    model.addConstr(trucks_A * data["truck_contents"]["A"]["A"] + trucks_B * data["truck_contents"]["B"]["A"] >= 240, name="raw_material_A")
    model.addConstr(trucks_A * data["truck_contents"]["A"]["B"] + trucks_B * data["truck_contents"]["B"]["B"] >= 80, name="raw_material_B")
    model.addConstr(trucks_A * data["truck_contents"]["A"]["C"] + trucks_B * data["truck_contents"]["B"]["C"] >= 120, name="raw_material_C")

    model.setObjective(data["freight_cost"]["A"] * trucks_A + data["freight_cost"]["B"] * trucks_B, gp.GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }

    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": {
            "trucks_A": model.getVarByName("trucks_A").X,
            "trucks_B": model.getVarByName("trucks_B").X
        }
    }