import random
import carla
from utils.walker_utils import get_walker_location_from_index

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

def control_vehicles_near_spectator(world, traffic_manager, spectator, safe_distance=10.0):
    """
    Stops vehicles managed by the TrafficManager if they get too close to the spectator.

    Args:
        world (carla.World): The CARLA world instance.
        traffic_manager (carla.TrafficManager): The TrafficManager instance.
        spectator (carla.Actor): The spectator actor.
        safe_distance (float): The minimum safe distance from the spectator in meters.
    """
    spectator_location = spectator.get_location()
    vehicles = world.get_actors().filter("vehicle.*")  # Get all vehicles in the world

    for vehicle in vehicles:
        vehicle_location = vehicle.get_location()
        distance = vehicle_location.distance(spectator_location)

        if distance < safe_distance:
            # Stop the vehicle if it is too close to the spectator
            print(f"Stopping vehicle {vehicle.id} (distance: {distance:.2f} meters)")
            vehicle.apply_control(carla.VehicleControl(throttle=0.0, brake=1.0))
        else:
            # Re-enable autopilot if the vehicle is at a safe distance
            if vehicle.attributes.get("role_name") == "autopilot":
                vehicle.set_autopilot(True, traffic_manager.get_port())
