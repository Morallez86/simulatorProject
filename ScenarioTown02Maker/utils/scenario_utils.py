import random
import carla
from utils.walker_utils import get_walker_location_from_index, is_valid_walker_spawn_index

def spawn_vehicle(world, bp_lib, model="vehicle.tesla.model3", transform=None):
    """
    Spawns a vehicle in the CARLA world.

    Args:
        world (carla.World): The CARLA world instance.
        bp_lib (carla.BlueprintLibrary): The blueprint library to find the vehicle blueprint.
        model (str): The model of the vehicle to spawn. Default is "vehicle.tesla.model3".
        transform (carla.Transform): The transform where the vehicle will be spawned. If None, a random spawn point is used.

    Returns:
        carla.Actor: The spawned vehicle actor.

    Raises:
        ValueError: If the vehicle blueprint is not found.
        RuntimeError: If the vehicle fails to spawn.
    """
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
        carla.Actor: The spawned walker actor.

    Raises:
        ValueError: If the walker blueprint is not found or the index is invalid.
        RuntimeError: If the walker fails to spawn.
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
    print(f"Spawning walker with location: {transform.location}")
    
    # Spawn the walker actor
    walker = world.spawn_actor(bp, transform)
    if not walker:
        raise RuntimeError(f"Failed to spawn walker at {transform.location}.")
    
    return walker

def vehicle_route(traffic_manager, spawn_points, vehicle, route):
    """
    Assigns a route to a vehicle in the CARLA simulator.

    Args:
        traffic_manager (carla.TrafficManager): The traffic manager instance.
        spawn_points (list): List of carla.Transform objects representing spawn points.
        vehicle (carla.Actor): The vehicle actor.
        route (list): List of indices representing the route.

    Raises:
        ValueError: If the vehicle or route is not provided.
        RuntimeError: If no spawn points are available.
    """
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

def walker_go_to_location(walker, spawn_points, walker_location, go_to_index_location, speed):
    """
    Assigns a route to a walker in the CARLA simulator, with custom offsets for sidewalks.

    Args:
        walker (carla.Actor): The walker actor.
        spawn_points (list): List of carla.Transform objects representing spawn points.
        walker_location (carla.Location): The current location of the walker.
        go_to_index_location (int): Index from spawn locations.
        speed (float): Speed of the walker. Default is 1.4 m/s.

    Returns:
        carla.Actor: The walker actor with updated control.

    Raises:
        ValueError: If the walker, route index, or spawn points are invalid.
    """
    if not walker or go_to_index_location is None:
        raise ValueError("Walker and route index must be provided.")

    if not isinstance(go_to_index_location, int):
        raise ValueError("Route index must be an integer.")

    if not spawn_points or not isinstance(spawn_points, list):
        raise ValueError("Spawn points must be a valid list of carla.Transform objects.")

    if go_to_index_location < 0 or go_to_index_location >= len(spawn_points):
        raise ValueError(f"Index {go_to_index_location} is out of range for the spawn points list.")

    # Get the transform for the destination
    destination_transform = get_walker_location_from_index(spawn_points, go_to_index_location)
    destination_transform.location.z = 0.0
    print(f"Destination location: {destination_transform.location}")

    # Calculate the vector between the current location and the destination
    print(f"Current location: {walker_location}")
    destination_location = destination_transform.location
    movement_vector = carla.Vector3D(
        x=destination_location.x - walker_location.x,
        y=destination_location.y - walker_location.y,
        z=destination_location.z - walker_location.z
    )
    print(f"Movement vector: {movement_vector}")

    # Normalize the movement vector to get the direction
    magnitude = (movement_vector.x**2 + movement_vector.y**2 + movement_vector.z**2)**0.5
    if magnitude > 0:
        direction = carla.Vector3D(
            x=movement_vector.x / magnitude,
            y=movement_vector.y / magnitude,
            z=movement_vector.z / magnitude
        )
    else:
        direction = carla.Vector3D(0.0, 0.0, 0.0)

    # Set the walker speed and direction
    walker_control = carla.WalkerControl(direction, speed, False)
    walker.apply_control(walker_control)

    return walker

def set_autopilot(vehicle, enable=True):
    """
    Enables or disables autopilot for a vehicle.

    Args:
        vehicle (carla.Actor): The vehicle actor.
        enable (bool): Whether to enable autopilot. Default is True.
    """
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

    Raises:
        Exception: If the sensors fail to attach.
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