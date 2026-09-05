import gurobipy as gp
from gurobipy import GRB

def solve():
    try:
        model = gp.Model("vrp")

        # Read data
        depot = data["depot"]
        customers = data["customers"]
        vehicles = data["vehicles"]
        max_vehicles = data["max_vehicles"]
        vehicle_capacity = data["vehicle_capacity"]
        coordinates = data["coordinates"]
        demand = data["demand"]
        time_window = data["time_window"]
        service_duration = data["service_duration"]
        arcs = data["arcs"]
        distance = data["distance"]
        big_m = data["big_m"]

        # Create variables
        x = model.addVars(len(arcs), vtype=GRB.BINARY, name="x")
        y = model.addVars(len(vehicles), len(customers), vtype=GRB.BINARY, name="y")
        q = model.addVars(len(vehicles), len(customers), vtype=GRB.BINARY, name="q")

        # Objective function
        model.setObjective(gp.quicksum(distance[arc] * x[i] for i in range(len(arcs))), GRB.MINIMIZE)

        # Constraints

        # Vehicle flow conservation
        for v in range(len(vehicles)):
            for c in customers:
                if c != depot:
                    model.addConstr(gp.quicksum(x[i] for i in range(len(arcs)) if i == (depot, c)) - \
                                    gp.quicksum(x[i] for i in range(len(arcs)) if i == (c, depot)) == y[v, c], "flow_conservation_" + str(v) + "_" + str(c))

            model.addConstr(gp.quicksum(x[i] for i in range(len(arcs)) if i == (depot, c)) - \
                            gp.quicksum(x[i] for i in range(len(arcs)) if i == (c, depot)) == 0, "flow_conservation_depot_" + str(v))

        # Customer visit constraints
        for v in range(len(vehicles)):
            for c in customers:
                if c != depot:
                    model.addConstr(y[v, c] <= q[v, c], "customer_visit_" + str(v) + "_" + str(c))

        # Vehicle capacity constraints
        for v in range(len(vehicles)):
            model.addConstr(gp.quicksum(demand[c] * y[v, c] for c in customers if c != depot) <= vehicle_capacity, "vehicle_capacity_" + str(v))

        # Time window constraints
        for c in customers:
            if c != depot:
                model.addConstr(gp.quicksum(x[i] for i in range(len(arcs)) if i == (depot, c)) * time_window[c][0] + \
                                 gp.quicksum(x[i] for i in range(len(arcs)) if i == (c, depot)) * time_window[c][1] <= big_m, "time_window_" + str(c))

        # Number of vehicles constraint
        model.addConstr(gp.quicksum(y[v, c] for v in range(len(vehicles)) for c in customers if c != depot) <= max_vehicles, "num_vehicles")

        # Solve the model
        model.optimize()

        if model.status == GRB.OPTIMAL:
            solution = {}
            solution["x"] = {}
            for i in range(len(arcs)):
                solution["x"][f"x_{i // 10}_{i % 10}"] = x[i].X

            solution["y"] = {}
            for v in range(len(vehicles)):
                for c in customers:
                    if c != depot:
                        solution["y"][f"x_v{v + 1}_{c}"] = y[v, c].X

            solution["q"] = {}
            for v in range(len(vehicles)):
                for c in customers:
                    if c != depot:
                        solution["q"][f"x_v{v + 1}_{c}"] = q[v, c].X

            return solution
        else:
            return {"status": model.status}

    except gp.GurobiError as e:
        print('Error code ' + str(e.errno) + ': ' + str(e))
        return {"status": GRB.INFEASIBLE}


solution = solve()