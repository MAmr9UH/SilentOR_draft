import gurobipy as gp
from gurobipy import GRB
import math
import json
def build_model(data: dict) -> tuple:
    # Initialize model
    model = gp.Model()

    # Basic data extraction
    depot = data["depot"]
    customers = list(data["customers"])  # [1..20]
    vehicles = list(data["vehicles"])    # [1..5]
    max_vehicles = data["max_vehicles"]
    capacity = data["vehicle_capacity"]
    coordinates = data["coordinates"]
    demand = {int(k): v for k, v in data["demand"].items()}
    time_window = {int(k): v for k, v in data["time_window"].items()}
    service_time = {i: data["service_duration"][str(i)] for i in customers}
    distance_map = data["distance"]
    big_M = data.get("big_m", 10000)

    # Helper distance function
    def get_dist(i, j):
        key = f"{i},{j}"
        if key in distance_map:
            return distance_map[key]
        rev = f"{j},{i}"
        if rev in distance_map:
            return distance_map[rev]
        # Fallback to Euclidean using coordinates
        xi, yi = coordinates[str(i)]
        xj, yj = coordinates[str(j)]
        return math.hypot(xi - xj, yi - yj)

    # Arc list
    arcs = [(int(i), int(j)) for (i, j) in data["arcs"]]

    # Build arc containers for constraints
    # arcs into node and arcs out of node
    arcs_in = {i: [] for i in range(0, max(customers) + 1)}
    arcs_out = {i: [] for i in range(0, max(customers) + 1)}
    arcs_from_dep = {v: [] for v in vehicles}
    arcs_to_dep = {v: [] for v in vehicles}

    for (i, j) in arcs:
        for v in vehicles:
            arcs_in[j].append((v, i))
            arcs_out[i].append((v, j))
            if i == 0:
                arcs_from_dep[v].append(j)
            if j == 0:
                arcs_to_dep[v].append(i)

    # Variable containers
    x_vars = {}  # key: (v,i,j) -> Var
    for (i, j) in arcs:
        for v in vehicles:
            key = (v, i, j)
            var_name = f"x_v{v}_{i}_{j}"
            x_vars[key] = model.addVar(vtype=GRB.BINARY, name=var_name)

    t_vars = {}  # key: (v,i) -> Var for time at customer i by vehicle v
    for v in vehicles:
        for i in customers:
            key = (v, i)
            var_name = f"t_v{v}_{i}"
            t_vars[key] = model.addVar(vtype=GRB.CONTINUOUS, name=var_name, lb=time_window[i][0], ub=time_window[i][1])

    # Collect all decision variables into a single dict for the output
    variables = {}

    # Add arc variables to output dict
    for (v, i, j), var in x_vars.items():
        key = f"x_v{v}_{i}_{j}"
        variables[key] = var

    # Add time variables to output dict
    for (v, i), var in t_vars.items():
        key = f"t_v{v}_{i}"
        variables[key] = var

    # Objective: minimize total travel distance
    obj = gp.quicksum(get_dist(i, j) * x_vars[(v, i, j)]
                      for (i, j) in arcs
                      for v in vehicles)
    model.setObjective(obj, GRB.MINIMIZE)

    # Time window constraints
    # 1) Time window bounds for all t_v_i
    for v in vehicles:
        for i in customers:
            model.addConstr(t_vars[(v, i)] >= time_window[i][0])
            model.addConstr(t_vars[(v, i)] <= time_window[i][1])

    # 2) Time propagation along arcs (i >= 1 to j >= 1)
    service_dur = 90  # fixed for all customers
    for (i, j) in arcs:
        if i == 0:
            # From depot to first customer
            for v in vehicles:
                model.addConstr(t_vars[(v, j)] >= get_dist(0, j) - big_M * (1 - x_vars[(v, 0, j)]))
        elif j == 0:
            # Arrival at depot has no explicit time variable; skip
            pass
        else:
            for v in vehicles:
                model.addConstr(t_vars[(v, j)] >=
                                t_vars[(v, i)] + service_dur + get_dist(i, j) - big_M * (1 - x_vars[(v, i, j)]))

    # Flow constraints:
    # Each customer must be visited exactly once (one incoming arc across all vehicles)
    for i in customers:
        model.addConstr(gp.quicksum(x_vars[(v, k, i)] for (v, k) in arcs_in[i]) == 1)

    # Each customer must have exactly one outgoing arc
    for i in customers:
        model.addConstr(gp.quicksum(x_vars[(v, i, j)] for (v, j) in arcs_out[i]) == 1)

    # Depot arc constraints per vehicle (each vehicle can depart at most once and return at most once)
    for v in vehicles:
        model.addConstr(gp.quicksum(x_vars[(v, 0, i)] for i in customers) <= 1)
        model.addConstr(gp.quicksum(x_vars[(v, i, 0)] for i in customers) <= 1)

    # Vehicle usage limit
    total_departs = gp.quicksum(x_vars[(v, 0, i)] for v in vehicles for i in customers)
    model.addConstr(total_departs <= max_vehicles)

    # Update model to integrate new vars (required by API when accessing after creation)
    model.update()

    # Return model and a flat dictionary of variables
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, "UNKNOWN")

    # Objective value
    if model.Status == GRB.OPTIMAL:
        objective_val = float(model.ObjVal)
    else:
        objective_val = float('inf')

    # Extract solution values for all variables
    solution = {}
    for key, var in variables.items():
        try:
            solution[key] = float(var.X)
        except:
            solution[key] = None

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }

if __name__ == "__main__":
    import json

    with open("/Users/mohamedamr/Downloads/EXP2_v41_TypedProbes_SemanticGate_Forensics/frozen_assets/Problems_main.json") as f:
        problems = json.load(f)

    # Find problem with id = 25
    problem = next(p for p in problems["pilot_problems"] if p["id"] == 25)

    # Extract the actual instance
    data = problem["data_instance"]

    result = solve(data)
    print(result)
