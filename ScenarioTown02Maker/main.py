# main.py
import glob
import os
import sys

try:
    sys.path.append(glob.glob('../PythonAPI/carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import time
from scenario.scenario_parser import load_scenario_from_json
from scenario.scenario_executor import ScenarioExecutor

def main():
    executor = None  # Ensure executor is defined for cleanup in finally block
    try:
        # Initialize CARLA client
        client = carla.Client("localhost", 2000) # type: ignore
        client.set_timeout(10.0)
        
        # Load world
        world = client.get_world()
        original_settings = world.get_settings()

        # Load traffic manager
        traffic_manager = client.get_trafficmanager()
        
        # Set asynchronous mode
        settings = world.get_settings()
        settings.synchronous_mode = False
        world.apply_settings(settings)
        
        # Initialize executor
        bp_lib = world.get_blueprint_library()
        executor = ScenarioExecutor(world, traffic_manager, bp_lib)
        
        # Load and execute scenario
        config = load_scenario_from_json("config/sample_scenario.json")
        executor.execute(config)
        
        # Main simulation loop
        try:
            while True:
                world.wait_for_tick() # Allow the simulation to run asynchronously
        except KeyboardInterrupt:
            print("\nScenario interrupted by user")
            
    except Exception as e:
        print(f"Error during scenario execution: {e}")
    finally:
        # Cleanup
        if executor:
            executor.cleanup()
        if 'world' in locals():
            world.apply_settings(original_settings)
        print("Scenario cleanup complete")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting...")