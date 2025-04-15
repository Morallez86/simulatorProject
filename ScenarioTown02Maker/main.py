# main.py
import carla
import time
from scenario.scenario_parser import load_scenario_from_json
from scenario.scenario_executor import ScenarioExecutor

def main():
    try:
        # Initialize CARLA client
        client = carla.Client("localhost", 2000)
        client.set_timeout(10.0)
        
        # Load world
        world = client.get_world()
        original_settings = world.get_settings()
        
        # Set synchronous mode for precise control
        settings = world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = 0.05
        world.apply_settings(settings)
        
        # Initialize executor
        bp_lib = world.get_blueprint_library()
        executor = ScenarioExecutor(world, bp_lib)
        
        # Load and execute scenario
        config = load_scenario_from_json("config/sample_scenario.json")
        executor.execute(config)
        
        # Main simulation loop
        try:
            while True:
                world.tick()
                time.sleep(0.05)
        except KeyboardInterrupt:
            print("\nScenario interrupted by user")
            
    except Exception as e:
        print(f"Error during scenario execution: {e}")
    finally:
        # Cleanup
        executor.cleanup()
        world.apply_settings(original_settings)
        print("Scenario cleanup complete")

if __name__ == "__main__":
    main()