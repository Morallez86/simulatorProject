import glob
import os
import sys

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import random

def spawn_vehicle(world, blueprint_library, x1, y1, z1, rotation):
    """Spawns a vehicle at the specified location."""
    vehicle_bp = random.choice(blueprint_library.filter('vehicle.*'))
    vehicle_transform = carla.Transform(
        carla.Location(x=x1, y=y1, z=z1),
        carla.Rotation(yaw=rotation)
    )
    vehicle = world.try_spawn_actor(vehicle_bp, vehicle_transform)
    if vehicle:
        print(f"Spawned vehicle: {vehicle.type_id} at {vehicle_transform.location}")
    else:
        print("Failed to spawn vehicle.")
    return vehicle


def attach_sensors_to_vehicle(world, walker_detection_sensor_bp, v2v_broadcast_sensor_bp, vehicle):
    """Attaches Walker Detection and V2V Broadcast sensors to a vehicle."""
    sensor_transform = carla.Transform(carla.Location(z=1))  # Place sensors above the vehicle

    walker_detection_sensor = None
    v2v_broadcast_sensor = None

    # Attach Walker Detection Sensor
    walker_detection_sensor = world.spawn_actor(
        walker_detection_sensor_bp,
        sensor_transform,
        attach_to=vehicle
    )
    if walker_detection_sensor:
        print("Walker Detection Sensor attached to the vehicle.")
        walker_detection_sensor.listen(lambda _: None)

    # Attach V2V Broadcast Sensor
    v2v_broadcast_sensor = world.spawn_actor(
        v2v_broadcast_sensor_bp,
        sensor_transform,
        attach_to=vehicle
    )
    if v2v_broadcast_sensor:
        print("V2V Broadcast Sensor attached to the vehicle.")
        v2v_broadcast_sensor.listen(lambda _: None)

    return walker_detection_sensor, v2v_broadcast_sensor


def spawn_walker_near_car(world, blueprint_library, vehicle_transform, x1, y1, z1):
    """Spawns a walker near the given vehicle transform."""
    walker_bp = random.choice(blueprint_library.filter('walker.*'))
    walker_transform = carla.Transform(
        vehicle_transform.location + carla.Location(x=x1, y=y1, z=z1),
        vehicle_transform.rotation
    )
    walker = world.spawn_actor(walker_bp, walker_transform)
    if walker:
        print(f"Spawned walker: {walker.type_id} at {walker_transform.location}")
    else:
        print("Failed to spawn walker.")
    return walker