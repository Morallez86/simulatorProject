import glob
import os
import sys
import random
import time

try:
    sys.path.append(glob.glob('../PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

def main():
    walkers = []
    walker_controllers = []
    try:
        # Initialize CARLA client
        client = carla.Client("localhost", 2000)
        client.set_timeout(10.0)

        # Get the world and blueprint library
        world = client.get_world()
        bp_lib = world.get_blueprint_library()

        # Get a random walker blueprint
        walker_bp = random.choice(bp_lib.filter('walker.pedestrian.*'))
        if walker_bp.has_attribute('is_invincible'):
            walker_bp.set_attribute('is_invincible', 'false')  # Make walker vulnerable

        # Get a random spawn point
        spawn_point = world.get_random_location_from_navigation()
        if not spawn_point:
            raise RuntimeError("No valid spawn point found.")
        transform = carla.Transform(spawn_point)

        # Spawn the walker
        walker = world.spawn_actor(walker_bp, transform)
        walkers.append(walker)
        print(f"Walker spawned at location: {walker.get_location()}")

        # Spawn the WalkerAIController
        walker_controller_bp = bp_lib.find('controller.ai.walker')
        walker_controller = world.spawn_actor(walker_controller_bp, carla.Transform(), attach_to=walker)
        walker_controllers.append(walker_controller)

        # Start the walker controller
        walker_controller.start()
        time.sleep(0.1)  # Allow the controller to initialize

        # Set a random destination
        random_destination = world.get_random_location_from_navigation()
        print(f"Random destination: {random_destination}")
        if not random_destination:
            raise RuntimeError("No valid random destination found.")

        # Validate the destination
        waypoint = world.get_map().get_waypoint(random_destination, project_to_road=False)
        if not waypoint:
            raise RuntimeError(f"Destination {random_destination} is not on a valid navigable area.")

        walker_controller.set_max_speed(1.4)  # Default walking speed
        walker_controller.go_to_location(random_destination)
        print(f"Walker moving to: {random_destination}")

        # Keep the script running to observe the walker
        print("Press Ctrl+C to stop.")
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Cleanup spawned walkers and controllers
        for walker_controller in walker_controllers:
            if walker_controller.is_alive:
                try:
                    walker_controller.stop()
                    walker_controller.destroy()
                except Exception as e:
                    print(f"Failed to destroy walker controller: {e}")
        for walker in walkers:
            if walker.is_alive:
                try:
                    walker.destroy()
                except Exception as e:
                    print(f"Failed to destroy walker: {e}")
        print("Cleanup complete.")

if __name__ == "__main__":
    main()