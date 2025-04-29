# scenario_executor.py
from utils.scenario_utils import spawn_vehicle, spawn_walker, set_autopilot, vehicle_route, attach_sensors_to_vehicle
import carla

class ScenarioExecutor:
    def __init__(self, world, traffic_manager, bp_lib, spawn_points, walker_manager):
        self.world = world
        self.traffic_manager = traffic_manager
        self.bp_lib = bp_lib
        self.spawn_points = spawn_points
        self.walker_manager = walker_manager
        self.spawned_actors = []
        
    def execute(self, config):
        try:
            
            # Relocate spectator to spawn point and attach sensors if needed
            spectator = self.world.get_spectator()
            if config.get("spectator"):
                for spectator_cfg in config["spectator"]:
                    spectator_loc = spectator_cfg["spawn_point"]
                    spawn_point = self.spawn_points[spectator_loc]
                    spectator.set_transform(spawn_point)

                    # Attach sensors to the spectator if spawn_walkersensor_v2v is True
                    if spectator_cfg.get("spawn_walkersensor_v2v", False):
                        spectator_sensors = attach_sensors_to_vehicle(self.world, self.bp_lib, spectator)
                        self.world.wait_for_tick()
                        self.spawned_actors.extend(spectator_sensors)

            # Spawn vehicles
            if not self.spawn_points:
                raise RuntimeError("No spawn points available in the map.")
            
            for vehicle_cfg in config.get("vehicles", []):
                try:
                    vehicle_loc = vehicle_cfg["spawn_point"]
                    spawn_point = self.spawn_points[vehicle_loc]
                    vehicle_loc = spawn_point.location
                    vehicle_rot = spawn_point.rotation

                    vehicle_transform = carla.Transform(vehicle_loc, vehicle_rot)  # type: ignore

                    vehicle = spawn_vehicle(
                        self.world,
                        self.bp_lib,
                        vehicle_cfg.get("model"),
                        vehicle_transform,
                    )
                    self.spawned_actors.append(vehicle)

                    # Attach sensors to the vehicle if spawn_walkersensor_v2v is True
                    if vehicle_cfg.get("spawn_walkersensor_v2v", False):
                        sensors = attach_sensors_to_vehicle(self.world, self.bp_lib, vehicle)
                        self.world.wait_for_tick()
                        self.spawned_actors.extend(sensors)

                    set_autopilot(vehicle, vehicle_cfg.get("autopilot", False))

                    vehicle_route_cfg = vehicle_cfg.get("route", [])
                    print(f"Vehicle route: {vehicle_route_cfg}")
                    vehicle_route(self.traffic_manager, self.spawn_points, vehicle, vehicle_route_cfg)
                except Exception as e:
                    print(f"Failed to spawn vehicle: {e}")
            
            # Spawn walkers
            percentagePedestriansCrossing = 1.0 
            self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
            self.world.wait_for_tick()

            for walker_cfg in config.get("walkers", []):
                try:
                    walker_spawn_index = walker_cfg["spawn_point"]
                    walker = spawn_walker(
                        self.world,
                        self.bp_lib,
                        walker_spawn_index,
                    )
                    self.spawned_actors.append(walker)

                    walker_route = walker_cfg["go_to_point"]
                    walker_speed = walker_cfg.get("speed", 1.4)

                    # Add the walker to the manager
                    self.walker_manager.add_walker(walker, walker_route, walker_speed)
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