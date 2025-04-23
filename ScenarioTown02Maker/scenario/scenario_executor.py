# scenario_executor.py
from utils.scenario_utils import spawn_vehicle, spawn_walker, set_autopilot, vehicle_route, walker_go_to_location, attach_sensors_to_vehicle
import carla

class ScenarioExecutor:
    def __init__(self, world, traffic_manager, bp_lib):
        self.world = world
        self.traffic_manager = traffic_manager
        self.bp_lib = bp_lib
        self.spawned_actors = []
        
    def execute(self, config):
        try:

            spawn_points = self.world.get_map().get_spawn_points()
            
            # Realocate spectator to spawn point
            spectator = self.world.get_spectator()
            print(f"Spectator location: {spectator.get_transform().location}")
            if config.get("spectator"):
                for spectator_cfg in config["spectator"]:
                    spectator_loc = spectator_cfg["spawn_point"]
                    spawn_point = spawn_points[spectator_loc]
                    spectator.set_transform(spawn_point)

            # Spawn vehicles
            if not spawn_points:
                raise RuntimeError("No spawn points available in the map.")
            
            if config.get("spawn_walkersensor_v2v", False):
                spectator = self.world.get_spectator()
                spectator_sensors = attach_sensors_to_vehicle(self.world, self.bp_lib, spectator)
                self.world.wait_for_tick()
                self.spawned_actors.extend(spectator_sensors)

            for vehicle_cfg in config.get("vehicles", []):
                try:
                    vehicle_loc = vehicle_cfg["spawn_point"]
                    spawn_point = spawn_points[vehicle_loc]
                    vehicle_loc = spawn_point.location
                    vehicle_rot = spawn_point.rotation

                    vehicle_transform = carla.Transform(vehicle_loc, vehicle_rot) # type: ignore

                    vehicle = spawn_vehicle(
                        self.world,
                        self.bp_lib,
                        vehicle_cfg.get("model"),
                        vehicle_transform,
                    )
                    self.spawned_actors.append(vehicle)

                    if config.get("spawn_walkersensor_v2v", False):
                        sensors = attach_sensors_to_vehicle(self.world, self.bp_lib, vehicle)
                        self.world.wait_for_tick()
                        self.spawned_actors.extend(sensors)
                    
                    set_autopilot(vehicle, vehicle_cfg.get("autopilot", False))

                    vehicle_route_cfg = vehicle_cfg.get("route", [])
                    print(f"Vehicle route: {vehicle_route_cfg}")
                    vehicle_route(self.traffic_manager, spawn_points, vehicle, vehicle_route_cfg)
                except Exception as e:
                    print(f"Failed to spawn vehicle: {e}")
            
            # Spawn walkers
            
            percentagePedestriansCrossing = 1.0 
            self.world.set_pedestrians_cross_factor(percentagePedestriansCrossing)
            self.world.wait_for_tick()

            for walker_cfg in config.get("walkers", []):
                try:
                    walker_spawn_index = walker_cfg["spawn_point"]
                    walker, walker_location= spawn_walker(
                        self.world,
                        self.bp_lib,
                        walker_spawn_index,
                    )

                    walker_go_to_location_index = walker_cfg["go_to_point"]
                    walker_go_to_location(
                        walker,
                        spawn_points,
                        walker_location,
                        walker_go_to_location_index,
                        speed=walker_cfg.get("speed"),
                    )

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