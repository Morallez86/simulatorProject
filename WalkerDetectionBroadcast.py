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

        # Find the 'sensor.other.walker_detection' blueprint
        walker_detection_sensor_bp = blueprint_library.find('sensor.other.walker_detection')
        if not walker_detection_sensor_bp:
            print("Walker Detection Sensor not found. Ensure it has been added and recompiled.")
            return
        
        # Find the 'sensor.other.v2v_broadcast' blueprint
        v2v_broadcast_sensor_bp = blueprint_library.find('sensor.other.v2v_broadcast')
        if not v2v_broadcast_sensor_bp:
            print("V2V Broadcast Sensor not found. Ensure it has been added and recompiled.")
            return

        # Find the spectator (camera) actor
        spectator = world.get_spectator()

        if spectator:
            # Attach the Walker Detection Sensor to the spectator's vehicle
            vehicle_transform = spectator.get_transform()
            sensor_transform = carla.Transform(carla.Location(z=1))  # Place it above the vehicle

            walker_detection_sensor = world.spawn_actor(
                walker_detection_sensor_bp, 
                sensor_transform, 
                attach_to=spectator
            )
            print("Walker Detection Sensor attached to the spectator vehicle.")

            v2v_broadcast_sensor = world.spawn_actor(
                v2v_broadcast_sensor_bp,
                sensor_transform,
                attach_to=spectator
            )
            print("V2V Broadcast Sensor attached to the spectator vehicle.")

            world_ref = weakref.ref(world)

            def walker_detection_callback(event):
                for walker_id, walker_data in event.items():
                    walker = world_ref().get_actor(walker_id)
                    if walker:
                        print(f"Detected walker: {walker.type_id} at {walker_data['Location']}")

            walker_detection_sensor.listen(walker_detection_callback)
            print("Listening to Walker Detection events...")

            def v2v_broadcast_callback(event):
                for vehicle_id, vehicle_data in event.items():
                    vehicle = world_ref().get_actor(vehicle_id)
                    if vehicle:
                        print(f"Detected vehicle: {vehicle.type_id} at {vehicle_data['Location']}")
            
            v2v_broadcast_sensor.listen(v2v_broadcast_callback)
            print("Listening to V2V Broadcast events...")

        # Wait for 5 seconds before spawning the walker
        time.sleep(5)

        # Spawn a walker near the car
        walker_bp = random.choice(blueprint_library.filter('walker.*'))
        spawn_points = world.get_map().get_spawn_points()
        walker_transform = carla.Transform(
            spawn_points[0].location + carla.Location(x=random.uniform(-1, 1), y=random.uniform(-1, 1), z=0.5),
            spawn_points[0].rotation
        )
        walker = world.spawn_actor(walker_bp, walker_transform)
        print(f"Spawned walker: {walker.type_id} at {walker_transform.location}")

        # Spawn an extra vehicle next to the walker
        vehicle_bp = random.choice(blueprint_library.filter('vehicle.*'))
        vehicle_transform = carla.Transform(
            walker_transform.location + carla.Location(x=0, y=4, z=0),  # Spawn vehicle near the walker
            walker_transform.rotation
        )
        extra_vehicle = world.spawn_actor(vehicle_bp, vehicle_transform)
        print(f"Spawned extra vehicle: {extra_vehicle.type_id} at {vehicle_transform.location}")

        # Attach the Walker Detection Sensor to the new vehicle
        extra_vehicle_walker_detection_sensor = world.spawn_actor(
            walker_detection_sensor_bp, 
            sensor_transform, 
            attach_to=extra_vehicle
        )
        print("Walker Detection Sensor attached to the extra vehicle.")

        # Attach the V2V Broadcast Sensor to the new vehicle
        extra_vehicle_v2v_broadcast_sensor = world.spawn_actor(
            v2v_broadcast_sensor_bp,
            sensor_transform,
            attach_to=extra_vehicle
        )
        print("V2V Broadcast Sensor attached to the extra vehicle.")

        # Define the callback for the extra vehicle's Walker Detection sensor
        def extra_vehicle_walker_callback(event):
            for walker_id, walker_data in event.items():
                walker = world_ref().get_actor(walker_id)
                if walker:
                    print(f"Extra vehicle detected a walker: {walker.type_id} at {walker_data['Location']}")

        extra_vehicle_walker_detection_sensor.listen(extra_vehicle_walker_callback)
        print("Extra vehicle listening to Walker Detection events...")

        # Define the callback for the extra vehicle's V2V Broadcast sensor
        def extra_vehicle_v2v_callback(event):
            for vehicle_id, vehicle_data in event.items():
                vehicle = world_ref().get_actor(vehicle_id)
                if vehicle:
                    print(f"Extra vehicle detected a vehicle: {vehicle.type_id} at {vehicle_data['Location']}")

        extra_vehicle_v2v_broadcast_sensor.listen(extra_vehicle_v2v_callback)
        print("Extra vehicle listening to V2V Broadcast events...")

        # Let the simulation run for a while
        time.sleep(90)

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Clean up
        if walker_detection_sensor:
            walker_detection_sensor.stop()
            walker_detection_sensor.destroy()
        if v2v_broadcast_sensor:
            v2v_broadcast_sensor.stop()
            v2v_broadcast_sensor.destroy()
        if 'walker' in locals():
            walker.destroy()
        if 'extra_vehicle' in locals():
            extra_vehicle.destroy()
        print("Cleaned up and exiting.")

if __name__ == '__main__':
    main()
