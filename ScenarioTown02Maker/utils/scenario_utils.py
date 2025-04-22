import random
import carla
import time
from utils.walker_utils import get_walker_location_from_index, is_valid_walker_spawn_index

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

def spawn_walker(world, bp_lib, walker_spawn_index):
    """
    Spawns a walker at the specified spawn index and assigns a WalkerAIController.

    Args:
        world (carla.World): The CARLA world instance.
        bp_lib (carla.BlueprintLibrary): The blueprint library.
        walker_spawn_index (int): The index of the spawn point.

    Returns:
        tuple: A tuple containing the walker actor and its AI controller.

    Raises:
        ValueError: If the walker blueprint is not found or the index is invalid.
        RuntimeError: If the walker or controller fails to spawn.
    """
    bp = bp_lib.find('walker.pedestrian.0001')
    if not bp:
        raise ValueError("Walker blueprint not found in blueprint library.")
    
    if walker_spawn_index is None:
        raise ValueError("Walker spawn index must be provided.")
    
    is_valid_index = is_valid_walker_spawn_index(walker_spawn_index)
    if not is_valid_index:
        raise ValueError(f"Invalid walker spawn index: {walker_spawn_index}")
    
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("No spawn points available in the map.")
    
    transform = get_walker_location_from_index(spawn_points, walker_spawn_index)
    
    # Spawn the walker actor
    walker = world.spawn_actor(bp, transform)
    if not walker:
        raise RuntimeError(f"Failed to spawn walker at {transform.location}.")
    
    # Spawn the WalkerAIController
    walker_controller_bp = bp_lib.find('controller.ai.walker')
    if not walker_controller_bp:
        raise ValueError("Walker AI controller blueprint not found in blueprint library.")
    
    walker_controller = world.spawn_actor(walker_controller_bp, carla.Transform(carla.Location(z=0.0)), attach_to=walker)
    if not walker_controller:
        raise RuntimeError("Failed to spawn WalkerAIController.")
    
    return walker, walker_controller

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

def walker_go_to_location(spawn_points, go_to_index_location, walker_controller, speed):
    """
    Assigns a route to a walker in the CARLA simulator, with custom offsets for sidewalks.

    Args:
        spawn_points (list): List of carla.Transform objects representing spawn points.
        go_to_index_location (int): Index from spawn locations.
        walker_controller (carla.WalkerAIController): The AI controller for the walker.
        speed (float): Speed of the walker. Default is 1.4 m/s.
    """
    if not walker_controller or go_to_index_location is None:
        raise ValueError("Walker controller and route index must be provided.")

    if not isinstance(go_to_index_location, int):
        raise ValueError("Route index must be an integer.")

    if not spawn_points or not isinstance(spawn_points, list):
        raise ValueError("Spawn points must be a valid list of carla.Transform objects.")

    if go_to_index_location < 0 or go_to_index_location >= len(spawn_points):
        raise ValueError(f"Index {go_to_index_location} is out of range for the spawn points list.")

    # Get the transform for the destination
    destination_transform = get_walker_location_from_index(spawn_points, go_to_index_location)
    destination_transform.location.z = 0.5
    print(f"Destination transform: {destination_transform}")
    print(f"Destination location: {destination_transform.location}")

    # Set the walker speed and destination
    walker_controller.start()
    walker_controller.go_to_location(destination_transform.location)
    walker_controller.set_max_speed(speed)

def set_autopilot(vehicle, enable=True):
    vehicle.set_autopilot(enable)

def attach_sensors_to_vehicle(world, bp_lib, vehicle):
    """
    Attaches walker detection and V2V broadcast sensors to a vehicle.

    Args:
        world (carla.World): The CARLA world instance.
        bp_lib (carla.BlueprintLibrary): The blueprint library to find sensor blueprints.
        vehicle (carla.Actor): The vehicle to which the sensors will be attached.

    Returns:
        list: A list of spawned sensor actors.
    """
    try:
        # Find sensor blueprints
        walker_detection_sensor_bp = bp_lib.find("sensor.other.walker_detection")
        v2v_broadcast_sensor_bp = bp_lib.find("sensor.other.v2v_broadcast")

        # Spawn walker detection sensor
        walker_detection_sensor = world.spawn_actor(
            walker_detection_sensor_bp,
            carla.Transform(carla.Location(z=1.0)),
            attach_to=vehicle
        )

        # Spawn V2V broadcast sensor
        v2v_broadcast_sensor = world.spawn_actor(
            v2v_broadcast_sensor_bp,
            carla.Transform(carla.Location(z=1.0)),
            attach_to=vehicle
        )

        # Start listening to sensors (no-op for now)
        walker_detection_sensor.listen(lambda _: None)
        v2v_broadcast_sensor.listen(lambda _: None)

        # Return the spawned sensors
        return [walker_detection_sensor, v2v_broadcast_sensor]

    except Exception as e:
        print(f"Failed to attach sensors to vehicle: {e}")
        return []