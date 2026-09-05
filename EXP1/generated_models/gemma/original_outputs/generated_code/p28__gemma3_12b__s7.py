import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables: container shipments
    x = {}
    for w in data["warehouses"]:
        for p in data["ports"]:
            x[w, p] = model.addVar(vtype=GRB.INTEGER, name=f"x_{w}_{p}", lb=0)

    # Decision variables: truck trips
    t = {}
    for w in data["warehouses"]:
        for p in data["ports"]:
            t[w, p] = model.addVar(vtype=GRB.INTEGER, name=f"t_{w}_{p}", lb=0)

    # Objective function: minimize total transportation cost
    objective = gp.quicksum(
        data["distance_km"][w][p] * data["cost_per_km_per_truck"] * t[w, p]
        for w in data["warehouses"]
        for p in data["ports"]
    )
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints: supply constraints
    for w in data["warehouses"]:
        supply_constraint = gp.quicksum(x[w, p] for p in data["ports"]) <= data["supply"][w]
        model.addConstr(supply_constraint, name=f"supply_{w}")

    # Constraints: demand constraints
    for p in data["ports"]:
        demand_constraint = gp.quicksum(x[w, p] for w in data["warehouses"]) >= data["demand"][p]
        model.addConstr(demand_constraint, name=f"demand_{p}")

    # Constraints: truck capacity constraints
    for w in data["warehouses"]:
        for p in data["ports"]:
            truck_capacity_constraint = t[w, p] <= x[w, p] * data["truck_capacity_containers"]
            model.addConstr(truck_capacity_constraint, name=f"truck_capacity_{w}_{p}")

    variables = {
        "x_Verona_Genoa": x["Verona", "Genoa"],
        "x_Verona_Venice": x["Verona", "Venice"],
        "x_Verona_Ancona": x["Verona", "Ancona"],
        "x_Verona_Naples": x["Verona", "Naples"],
        "x_Verona_Bari": x["Verona", "Bari"],
        "x_Perugia_Genoa": x["Perugia", "Genoa"],
        "x_Perugia_Venice": x["Perugia", "Venice"],
        "x_Perugia_Ancona": x["Perugia", "Ancona"],
        "x_Perugia_Naples": x["Perugia", "Naples"],
        "x_Perugia_Bari": x["Perugia", "Bari"],
        "x_Rome_Genoa": x["Rome", "Genoa"],
        "x_Rome_Venice": x["Rome", "Venice"],
        "x_Rome_Ancona": x["Rome", "Ancona"],
        "x_Rome_Naples": x["Rome", "Naples"],
        "x_Rome_Bari": x["Rome", "Bari"],
        "x_Pescara_Genoa": x["Pescara", "Genoa"],
        "x_Pescara_Venice": x["Pescara", "Venice"],
        "x_Pescara_Ancona": x["Pescara", "Ancona"],
        "x_Pescara_Naples": x["Pescara", "Naples"],
        "x_Pescara_Bari": x["Pescara", "Bari"],
        "x_Taranto_Genoa": x["Taranto", "Genoa"],
        "x_Taranto_Venice": x["Taranto", "Venice"],
        "x_Taranto_Ancona": x["Taranto", "Ancona"],
        "x_Taranto_Naples": x["Taranto", "Naples"],
        "x_Taranto_Bari": x["Taranto", "Bari"],
        "x_Lamezia_Genoa": x["Lamezia", "Genoa"],
        "x_Lamezia_Venice": x["Lamezia", "Venice"],
        "x_Lamezia_Ancona": x["Lamezia", "Ancona"],
        "x_Lamezia_Naples": x["Lamezia", "Naples"],
        "x_Lamezia_Bari": x["Lamezia", "Bari"],
        "t_Verona_Genoa": t["Verona", "Genoa"],
        "t_Verona_Venice": t["Verona", "Venice"],
        "t_Verona_Ancona": t["Verona", "Ancona"],
        "t_Verona_Naples": t["Verona", "Naples"],
        "t_Verona_Bari": t["Verona", "Bari"],
        "t_Perugia_Genoa": t["Perugia", "Genoa"],
        "t_Perugia_Venice": t["Perugia", "Venice"],
        "t_Perugia_Ancona": t["Perugia", "Ancona"],
        "t_Perugia_Naples": t["Perugia", "Naples"],
        "t_Perugia_Bari": t["Perugia", "Bari"],
        "t_Rome_Genoa": t["Rome", "Genoa"],
        "t_Rome_Venice": t["Rome", "Venice"],
        "t_Rome_Ancona": t["Rome", "Ancona"],
        "t_Rome_Naples": t["Rome", "Naples"],
        "t_Rome_Bari": t["Rome", "Bari"],
        "t_Pescara_Genoa": t["Pescara", "Genoa"],
        "t_Pescara_Venice": t["Pescara", "Venice"],
        "t_Pescara_Ancona": t["Pescara", "Ancona"],
        "t_Pescara_Naples": t["Pescara", "Naples"],
        "t_Pescara_Bari": t["Pescara", "Bari"],
        "t_Taranto_Genoa": t["Taranto", "Genoa"],
        "t_Taranto_Venice": t["Taranto", "Venice"],
        "t_Taranto_Ancona": t["Taranto", "Ancona"],
        "t_Taranto_Naples": t["Taranto", "Naples"],
        "t_Taranto_Bari": t["Taranto", "Bari"],
        "t_Lamezia_Genoa": t["Lamezia", "Genoa"],
        "t_Lamezia_Venice": t["Lamezia", "Venice"],
        "t_Lamezia_Ancona": t["Lamezia", "Ancona"],
        "t_Lamezia_Naples": t["Lamezia", "Naples"],
        "t_Lamezia_Bari": t["Lamezia", "Bari"]
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "x_Verona_Genoa": variables["x_Verona_Genoa"].X,
        "x_Verona_Venice": variables["x_Verona_Venice"].X,
        "x_Verona_Ancona": variables["x_Verona_Ancona"].X,
        "x_Verona_Naples": variables["x_Verona_Naples"].X,
        "x_Verona_Bari": variables["x_Verona_Bari"].X,
        "x_Perugia_Genoa": variables["x_Perugia_Genoa"].X,
        "x_Perugia_Venice": variables["x_Perugia_Venice"].X,
        "x_Perugia_Ancona": variables["x_Perugia_Ancona"].X,
        "x_Perugia_Naples": variables["x_Perugia_Naples"].X,
        "x_Perugia_Bari": variables["x_Perugia_Bari"].X,
        "x_Rome_Genoa": variables["x_Rome_Genoa"].X,
        "x_Rome_Venice": variables["x_Rome_Venice"].X,
        "x_Rome_Ancona": variables["x_Rome_Ancona"].X,
        "x_Rome_Naples": variables["x_Rome_Naples"].X,
        "x_Rome_Bari": variables["x_Rome_Bari"].X,
        "x_Pescara_Genoa": variables["x_Pescara_Genoa"].X,
        "x_Pescara_Venice": variables["x_Pescara_Venice"].X,
        "x_Pescara_Ancona": variables["x_Pescara_Ancona"].X,
        "x_Pescara_Naples": variables["x_Pescara_Naples"].X,
        "x_Pescara_Bari": variables["x_Pescara_Bari"].X,
        "x_Taranto_Genoa": variables["x_Taranto_Genoa"].X,
        "x_Taranto_Venice": variables["x_Taranto_Venice"].X,
        "x_Taranto_Ancona": variables["x_Taranto_Ancona"].X,
        "x_Taranto_Naples": variables["x_Taranto_Naples"].X,
        "x_Taranto_Bari": variables["x_Taranto_Bari"].X,
        "x_Lamezia_Genoa": variables["x_Lamezia_Genoa"].X,
        "x_Lamezia_Venice": variables["x_Lamezia_Venice"].X,
        "x_Lamezia_Ancona": variables["x_Lamezia_Ancona"].X,
        "x_Lamezia_Naples": variables["x_Lamezia_Naples"].X,
        "x_Lamezia_Bari": variables["x_Lamezia_Bari"].X,
        "t_Verona_Genoa": variables["t_Verona_Genoa"].X,
        "t_Verona_Venice": variables["t_Verona_Venice"].X,
        "t_Verona_Ancona": variables["t_Verona_Ancona"].X,
        "t_Verona_Naples": variables["t_Verona_Naples"].X,
        "t_Verona_Bari": variables["t_Verona_Bari"].X,
        "t_Perugia_Genoa": variables["t_Perugia_Genoa"].X,
        "t_Perugia_Venice": variables["t_Perugia_Venice"].X,
        "t_Perugia_Ancona": variables["t_Perugia_Ancona"].X,
        "t_Perugia_Naples": variables["t_Perugia_Naples"].X,
        "t_Perugia_Bari": variables["t_Perugia_Bari"].X,
        "t_Rome_Genoa": variables["t_Rome_Genoa"].X,
        "t_Rome_Venice": variables["t_Rome_Venice"].X,
        "t_Rome_Ancona": variables["t_Rome_Ancona"].X,
        "t_Rome_Naples": variables["t_Rome_Naples"].X,
        "t_Rome_Bari": variables["t_Rome_Bari"].X,
        "t_Pescara_Genoa": variables["t_Pescara_Genoa"].X,
        "t_Pescara_Venice": variables["t_Pescara_Venice"].X,
        "t_Pescara_Ancona": variables["t_Pescara_Ancona"].X,
        "t_Pescara_Naples": variables["t_Pescara_Naples"].X,
        "t_Pescara_Bari": variables["t_Pescara_Bari"].X,
        "t_Taranto_Genoa": variables["t_Taranto_Genoa"].X,
        "t_Taranto_Venice": variables["t_Taranto_Venice"].X,
        "t_Taranto_Ancona": variables["t_Taranto_Ancona"].X,
        "t_Taranto_Naples": variables["t_Taranto_Naples"].X,
        "t_Taranto_Bari": variables["t_Taranto_Bari"].X,
        "t_Lamezia_Genoa": variables["t_Lamezia_Genoa"].X,
        "t_Lamezia_Venice": variables["t_Lamezia_Venice"].X,
        "t_Lamezia_Ancona": variables["t_Lamezia_Ancona"].X,
        "t_Lamezia_Naples": variables["t_Lamezia_Naples"].X,
        "t_Lamezia_Bari": variables["t_Lamezia_Bari"].X
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }