import glob
import os
import sys
import time
import random
import carla

def is_location_valid(world, location):
    """ Check if the location is valid for spawning (not colliding with existing actors) """
    for actor in world.get_actors():
        if actor.type_id.startswith('walker.pedestrian'):
            continue  # Skip already spawned pedestrians
        if actor.get_location().distance(location) < 4.0:  # Increased radius check
            return False
    return True

def spawn_pedestrians(world, pedestrian_blueprints, number_of_pedestrians):
    """ Spawn pedestrians and their controllers. """
    pedestrians_list = []
    
    for _ in range(number_of_pedestrians):
        for attempt in range(20):  # Allow up to 20 attempts
            spawn_point = world.get_random_location_from_navigation()

            if spawn_point is not None and is_location_valid(world, spawn_point):
                pedestrian_bp = random.choice(pedestrian_blueprints)
                
                # Create a Transform for the pedestrian (with zero rotation)
                transform = carla.Transform(spawn_point, carla.Rotation(0, 0, 0))
                
                # Attempt to spawn the pedestrian
                try:
                    pedestrian = world.spawn_actor(pedestrian_bp, transform)
                    pedestrians_list.append(pedestrian)
                    print(f'Spawned pedestrian: {pedestrian.id} at {spawn_point}')
                    break  # Exit the retry loop if successful
                except RuntimeError as e:
                    print(f'Failed to spawn pedestrian at {spawn_point}: {e}')
            else:
                print(f'Attempt {attempt + 1} failed to find a valid spawn location for a pedestrian.')
    
    # Spawn pedestrian controllers
    walker_controller_bp = world.get_blueprint_library().find('controller.ai.walker')
    controllers_list = []

    for pedestrian in pedestrians_list:
        try:
            controller = world.spawn_actor(walker_controller_bp, carla.Transform(), pedestrian)
            controllers_list.append(controller)
            print(f'Spawned controller for pedestrian: {pedestrian.id}')
        except RuntimeError as e:
            print(f'Failed to spawn controller for pedestrian {pedestrian.id}: {e}')

    # Set targets and start movement
    for controller in controllers_list:
        target_location = world.get_random_location_from_navigation()
        if target_location:
            controller.start()
            controller.go_to_location(target_location)
            controller.set_max_speed(10)  # Adjust the speed here

    return pedestrians_list, controllers_list

def is_pedestrian_near_vehicle(vehicle, pedestrians, radius=20.0):
    """ Check if there is any pedestrian within a specified radius of the vehicle. """
    vehicle_location = vehicle.get_location()
    for pedestrian in pedestrians:
        if pedestrian.get_location().distance(vehicle_location) < radius:
            return True
    return False

def toggle_vehicle_hazard_lights(vehicle_actors, pedestrians, radius=20.0):
    """ Toggle hazard lights based on pedestrian proximity. """
    for vehicle in vehicle_actors.values():
        if is_pedestrian_near_vehicle(vehicle, pedestrians, radius):
            vehicle.set_light_state(carla.VehicleLightState.All)  # Turn on all lights (hazard lights)
        else:
            vehicle.set_light_state(carla.VehicleLightState.NONE)  # Turn off all lights

def spawn_vehicles(client, world, traffic_manager, blueprint_library, spawn_points, number_of_vehicles):
    """ Spawn vehicles with autopilot in batch mode and store their actor IDs. """
    # List of selected vehicles (as strings)
    selected_vehicles = [
        'vehicle.ford.ambulance',
        'vehicle.audi.etron',
        'vehicle.audi.tt',
        'vehicle.chevrolet.impala',
        'vehicle.tesla.cybertruck',
        'vehicle.dodge.charger_2020',
        'vehicle.dodge.charger_police_2020',
        'vehicle.carlamotors.firetruck',
        'vehicle.ford.crown',
        'vehicle.lincoln.mkz_2020',
        'vehicle.lincoln.mkz_2017',
        'vehicle.mercedes.coupe',
        'vehicle.mini.cooper_s_2021',
        'vehicle.ford.mustang',
        'vehicle.mercedes.sprinter',
        'vehicle.tesla.model3',
        'vehicle.volkswagen.t2_2021',
        'vehicle.volkswagen.t2'
    ]
    blueprints = [blueprint_library.find(vehicle) for vehicle in selected_vehicles]
    batch = []
    vehicles_list = []

    # Randomize spawn points for variety
    random.shuffle(spawn_points)

    for n, transform in enumerate(spawn_points):
        if n >= number_of_vehicles:
            break
        blueprint = random.choice(blueprints)
        
        if blueprint.has_attribute('color'):
            color = random.choice(blueprint.get_attribute('color').recommended_values)
            blueprint.set_attribute('color', color)

        if blueprint.has_attribute('driver_id'):
            driver_id = random.choice(blueprint.get_attribute('driver_id').recommended_values)
            blueprint.set_attribute('driver_id', driver_id)

        blueprint.set_attribute('role_name', 'autopilot')
        batch.append(carla.command.SpawnActor(blueprint, transform)
            .then(carla.command.SetAutopilot(carla.command.FutureActor, True, traffic_manager.get_port())))

    # Execute the batch spawn
    responses = client.apply_batch_sync(batch, True)  # Use `client` instead of `world.get_client()`
    for response in responses:
        if response.error:
            print(f'Error spawning vehicle: {response.error}')
        else:
            vehicles_list.append(response.actor_id)

    return vehicles_list

def broadcast_v2v_data(vehicle_actors, v2v_data):
    """ Broadcast each vehicle's position and speed to the v2v_data dictionary. """
    for actor_id, vehicle in vehicle_actors.items():
        # Gather vehicle's position and speed data
        vehicle_location = vehicle.get_location()
        vehicle_speed = vehicle.get_velocity().length()
        
        # Store or update in shared dictionary
        v2v_data[actor_id] = {
            'location': vehicle_location,
            'speed': vehicle_speed,
        }

def process_v2v_data(vehicle, v2v_data, proximity_threshold=30.0):
    """ Process received data from nearby vehicles for decision making. """
    vehicle_location = vehicle.get_location()
    
    for other_id, other_data in v2v_data.items():
        if other_id == vehicle.id:
            continue  # Skip self

        # Calculate distance to other vehicle
        other_location = other_data['location']
        distance = vehicle_location.distance(other_location)
        
        if distance < proximity_threshold:
            # Example action: print information about the nearby vehicle
            print(f"Vehicle {vehicle.id} is near vehicle {other_id}. Distance: {distance:.2f} meters.")
            # Add any additional processing, like speed adjustments or collision avoidance here

def main():
    # Connect to the CARLA server
    client = carla.Client('localhost', 2000)
    client.set_timeout(10.0)
    
    # Get the world and setup traffic manager
    world = client.get_world()
    traffic_manager = client.get_trafficmanager(8000)
    traffic_manager.set_global_distance_to_leading_vehicle(2.5)
    
    # Get the blueprint library
    blueprint_library = world.get_blueprint_library()
    pedestrian_blueprints = blueprint_library.filter('walker.pedestrian.*')
    spawn_points = world.get_map().get_spawn_points()
    
    # Number of vehicles and pedestrians to spawn
    number_of_vehicles = 20
    number_of_pedestrians = 10

    # Spawn vehicles in batch using the function
    vehicle_actor_ids = spawn_vehicles(client, world, traffic_manager, blueprint_library, spawn_points, number_of_vehicles)
    vehicle_actors = {actor_id: world.get_actor(actor_id) for actor_id in vehicle_actor_ids}

    # Spawn pedestrians
    pedestrians_list, controllers_list = spawn_pedestrians(world, pedestrian_blueprints, number_of_pedestrians)

    # Initialize a shared dictionary for V2V data
    v2v_data = {}

    try:
        while True:
            # Wait for the next tick to keep in sync with the simulation
            world.wait_for_tick()

            # Broadcast each vehicle's V2V data to the shared dictionary
            broadcast_v2v_data(vehicle_actors, v2v_data)

            # Toggle hazard lights based on pedestrian proximity
            toggle_vehicle_hazard_lights(vehicle_actors, pedestrians_list, radius=20.0)
            
            # Process V2V data for each vehicle to respond to nearby vehicles
            for vehicle in vehicle_actors.values():
                process_v2v_data(vehicle, v2v_data)
                
    finally:
        print('Destroying vehicles and pedestrians...')
        client.apply_batch([carla.command.DestroyActor(x) for x in vehicle_actor_ids + [p.id for p in pedestrians_list + controllers_list]])

if __name__ == '__main__':
    main()
