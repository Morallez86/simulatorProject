import random
import carla

def spawn_vehicle(world, bp_lib, model="vehicle.tesla.model3", transform=None):
    bp = bp_lib.find(model)
    if not bp:
        raise ValueError(f"Vehicle model '{model}' not found in blueprint library.")
    
    if transform is None:
        transform = random.choice(world.get_map().get_spawn_points())
    
    vehicle = world.spawn_actor(bp, transform)
    if not vehicle:
        raise RuntimeError(f"Failed to spawn vehicle '{model}' at {transform.location}.")
    return vehicle

def spawn_walker(world, bp_lib, transform):
    bp = bp_lib.find('walker.pedestrian.0001')
    if not bp:
        raise ValueError("Walker blueprint not found in blueprint library.")
    
    if transform is None:
        transform = random.choice(world.get_map().get_spawn_points())
    
    walker = world.spawn_actor(bp, transform)
    if not walker:
        raise RuntimeError(f"Failed to spawn walker at {transform.location}.")
    return walker

def vehicle_route(traffic_manager, spawn_points, vehicle, route):
    if not vehicle or not route:
        raise ValueError("Vehicle and route must be provided.")

    if not spawn_points:
        raise RuntimeError("No spawn points available in the map.")
    
    route_1 = []
    for ind in route:
        route_1.append(spawn_points[ind].location)
    
    traffic_manager.random_left_lanechange_percentage(vehicle, 0)
    traffic_manager.random_right_lanechange_percentage(vehicle, 0)
    traffic_manager.auto_lane_change(vehicle, False)
    traffic_manager.set_path(vehicle, route_1)


def set_autopilot(vehicle, enable=True):
    vehicle.set_autopilot(enable)