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

        # Find the spectator (camera) actor
        spectator = world.get_spectator()

        if spectator:
            # Attach the Safe Distance Sensor to the spectator's vehicle
            # Assuming the spectator is following a vehicle, you can use the vehicle transform
            vehicle_transform = spectator.get_transform()

            sensor_transform = carla.Transform(carla.Location(z=0))  # Place it above the vehicle
            safe_distance_sensor = world.spawn_actor(
                safe_distance_sensor_bp, 
                sensor_transform, 
                attach_to=spectator
            )
            print("Safe Distance Sensor attached to the spectator vehicle.")

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
        spawn_points = world.get_map().get_spawn_points()
        walker_transform = carla.Transform(
            spawn_points[0].location + carla.Location(x=random.uniform(-1, 1), y=random.uniform(-1, 1), z=0.5),
            spawn_points[0].rotation
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
        if 'walker' in locals():
            walker.destroy()
        print("Cleaned up and exiting.")

if __name__ == '__main__':
    main()
