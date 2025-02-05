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
import weakref
import time
import random

def main():
    try:
        # Connect to the CARLA server
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        
        # Get the world
        world = client.get_world()

        # Get the blueprint library
        blueprint_library = world.get_blueprint_library()

        # Find the 'sensor.other.safe_distance' blueprint
        safe_distance_sensor_bp = blueprint_library.find('sensor.other.safe_distance')
        if not safe_distance_sensor_bp:
            print("Safe Distance Sensor not found. Ensure it has been added and recompiled.")
            return

        # Spawn a vehicle to attach the sensor to
        vehicle_bp = blueprint_library.filter('vehicle.*')[0]  # Select the first vehicle
        spawn_points = world.get_map().get_spawn_points()
        vehicle_transform = spawn_points[0] if spawn_points else carla.Transform()
        
        vehicle = world.spawn_actor(vehicle_bp, vehicle_transform)
        print(f"Spawned vehicle: {vehicle.type_id} at {vehicle_transform.location}")

        # Spawn the Safe Distance Sensor
        sensor_transform = carla.Transform(carla.Location(z=0))  # Place it above the vehicle
        safe_distance_sensor = world.spawn_actor(
            safe_distance_sensor_bp, 
            sensor_transform, 
            attach_to=vehicle
        )
        print("Safe Distance Sensor attached to the vehicle.")

        # Weak reference to the world to use inside the callback
        world_ref = weakref.ref(world)

        # Define the callback function
        def safe_distance_callback(event):
            for actor_id in event:
                vehicle = world_ref().get_actor(actor_id)
                print(f"Vehicle too close: {vehicle.type_id}")

        # Start listening for Safe Distance events
        safe_distance_sensor.listen(safe_distance_callback)
        print("Listening to Safe Distance events...")

        # Wait for 5 seconds before spawning the walker
        time.sleep(10)

        # Spawn a walker near the car
        walker_bp = random.choice(blueprint_library.filter('walker.*'))
        walker_transform = carla.Transform(
            vehicle_transform.location + carla.Location(x=random.uniform(-1, 1), y=random.uniform(-1, 1), z=0.5),
            vehicle_transform.rotation
        )
        walker = world.spawn_actor(walker_bp, walker_transform)
        print(f"Spawned walker: {walker.type_id} at {walker_transform.location}")

        # Let the simulation run for a while
        time.sleep(30)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        if safe_distance_sensor:
            safe_distance_sensor.stop()
            safe_distance_sensor.destroy()
        if vehicle:
            vehicle.destroy()
        if 'walker' in locals():
            walker.destroy()
        print("Cleaned up and exiting.")

if __name__ == '__main__':
    main()