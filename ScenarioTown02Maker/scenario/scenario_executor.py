# scenario_executor.py
from utils.scenario_utils import spawn_vehicle, spawn_walker, set_autopilot, vehicle_route
import carla

class ScenarioExecutor:
    def __init__(self, world, traffic_manager, bp_lib):
        self.world = world
        self.traffic_manager = traffic_manager
        self.bp_lib = bp_lib
        self.spawned_actors = []
        
    def execute(self, config):
        try:         
            # Spawn vehicles
            for vehicle_cfg in config.get("vehicles", []):
                try:
                    vehicle_loc = vehicle_cfg["spawn_point"]
                    spawn_points = self.world.get_map().get_spawn_points()
                    if not spawn_points:
                        raise RuntimeError("No spawn points available in the map.")
                    spawn_point = spawn_points[vehicle_loc]
                    vehicle_loc = spawn_point.location
                    vehicle_rot = spawn_point.rotation

                    vehicle_transform = carla.Transform(vehicle_loc, vehicle_rot)

                    vehicle = spawn_vehicle(
                        self.world,
                        self.bp_lib,
                        vehicle_cfg.get("model"),
                        vehicle_transform,
                    )
                    self.spawned_actors.append(vehicle)
                    
                    set_autopilot(vehicle, vehicle_cfg.get("autopilot", False))

                    vehicle_route_cfg = vehicle_cfg.get("route", [])
                    print(f"Vehicle route: {vehicle_route_cfg}")
                    vehicle_route(self.traffic_manager, spawn_points, vehicle, vehicle_route_cfg)
                except Exception as e:
                    print(f"Failed to spawn vehicle: {e}")
            
            # Spawn walkers
            for walker_cfg in config.get("walkers", []):
                try:
                    walker_loc = walker_cfg["spawn_location"]
                    walker_transform = carla.Transform(carla.Location(**walker_loc))
                    walker = spawn_walker(self.world, self.bp_lib, walker_transform)
                    self.spawned_actors.append(walker)
                except Exception as e:
                    print(f"Failed to spawn walker: {e}")
                    
        except Exception as e:
            self.cleanup()
            raise
            
    def cleanup(self):
        for actor in self.spawned_actors:
            if actor.is_alive:
                try:
                    if hasattr(actor, 'stop'):
                        actor.stop()
                    actor.destroy()
                except Exception as e:
                    print(f"Failed to destroy actor: {e}")
        self.spawned_actors = []