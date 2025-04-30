import carla

# Custom index lists for sidewalk zones
LEFT_SIDEWALK = [27, 94, 25, 29, 31, 86, 33, 35, 60, 70, 58, 84, 62, 64, 66, 68, 50, 48, 88, 54, 39, 37, 91, 43, 45, 47]
RIGHT_SIDEWALK = [28, 95, 26, 30, 32, 34, 36, 61, 71, 59, 63, 83, 65, 67, 69, 57, 49, 89, 55, 38, 40, 92, 42, 90, 44, 46]
TOP_SIDEWALK = [23, 21, 19, 13, 15, 80, 82, 76, 78, 72, 74, 11, 9, 85, 7, 5, 99, 97, 3]
BOTTOM_SIDEWALK = [24, 22, 18, 14, 93, 16, 81, 0, 77, 79, 73, 75, 12, 10, 8, 6, 96, 100, 98, 4]
UNAVAILABLE_SPAWN_INDEXES = [1, 2, 17, 20, 41, 42, 51, 52, 53, 56, 87]

def get_walker_offset_for_index(index):
    """
    Returns an offset for a walker based on its spawn index.

    Args:
        index (int): The spawn index of the walker.

    Returns:
        tuple: A tuple (x, y, z) representing the offset to apply to the spawn location.
    """
    if index in LEFT_SIDEWALK:
        return (0, -4, 0)
    elif index in RIGHT_SIDEWALK:
        return (0, 4, 0)
    elif index in TOP_SIDEWALK:
        return (4, 0, 0)
    elif index in BOTTOM_SIDEWALK:
        return (-4, 0, 0)
    return (0, 0, 0)  # Default or fallback

def get_walker_location_from_index(spawn_points, index):
    """
    Calculates the transform for a walker based on its spawn index and offset.

    Args:
        spawn_points (list): List of carla.Transform objects representing spawn points.
        index (int): The spawn index of the walker.

    Returns:
        carla.Transform: The transform for the walker, including the offset.

    Raises:
        IndexError: If the index is out of range for the spawn points list.
    """
    if index >= len(spawn_points):
        raise IndexError("Invalid spawn point index.")

    transform = spawn_points[index]
    offset = get_walker_offset_for_index(index)

    new_location = carla.Location(  # type: ignore
        x=transform.location.x + offset[0],
        y=transform.location.y + offset[1],
        z=transform.location.z + offset[2],
    )

    return carla.Transform(new_location, transform.rotation)  # type: ignore

def is_valid_walker_spawn_index(index):
    """
    Checks if the given spawn index is valid.

    Args:
        index (int): The spawn index to check.

    Returns:
        bool: True if the index is valid, False otherwise.
    """
    if index < 0 or index > 100:  # Check if the index is out of range
        return False
    if index in UNAVAILABLE_SPAWN_INDEXES:  # Check if the index is in the unavailable list
        return False
    return True

def spawn_walker(world, bp_lib, walker_spawn_index):
    """
    Spawns a walker at the specified spawn index and assigns a WalkerAIController.

    Args:
        world (carla.World): The CARLA world instance.
        bp_lib (carla.BlueprintLibrary): The blueprint library.
        walker_spawn_index (int): The index of the spawn point.

    Returns:
        carla.Actor: The spawned walker actor.

    Raises:
        ValueError: If the walker blueprint is not found or the index is invalid.
        RuntimeError: If the walker fails to spawn.
    """
    bp = bp_lib.find('walker.pedestrian.0001')
    if not bp:
        raise ValueError("Walker blueprint not found in blueprint library.")
    
    if walker_spawn_index is None:
        raise ValueError("Walker spawn index must be provided.")
    
    is_valid_index = is_valid_walker_spawn_index(walker_spawn_index)
    if not is_valid_index:
        raise ValueError(f"Invalid walker spawn index: {walker_spawn_index}")
    
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("No spawn points available in the map.")
    
    transform = get_walker_location_from_index(spawn_points, walker_spawn_index)
    print(f"Spawning walker with location: {transform.location}")
    
    # Spawn the walker actor
    walker = world.spawn_actor(bp, transform)
    if not walker:
        raise RuntimeError(f"Failed to spawn walker at {transform.location}.")
    
    return walker

def walker_go_to_location(walker, spawn_points, walker_location, go_to_index_location, speed):
    """
    Assigns a route to a walker in the CARLA simulator, with custom offsets for sidewalks.

    Args:
        walker (carla.Actor): The walker actor.
        spawn_points (list): List of carla.Transform objects representing spawn points.
        walker_location (carla.Location): The current location of the walker.
        go_to_index_location (int): Index from spawn locations.
        speed (float): Speed of the walker. Default is 1.4 m/s.

    Returns:
        carla.Actor: The walker actor with updated control.

    Raises:
        ValueError: If the walker, route index, or spawn points are invalid.
    """
    if not walker or go_to_index_location is None:
        raise ValueError("Walker and route index must be provided.")

    if not isinstance(go_to_index_location, int):
        raise ValueError("Route index must be an integer.")

    if not spawn_points or not isinstance(spawn_points, list):
        raise ValueError("Spawn points must be a valid list of carla.Transform objects.")

    if go_to_index_location < 0 or go_to_index_location >= len(spawn_points):
        raise ValueError(f"Index {go_to_index_location} is out of range for the spawn points list.")

    # Get the transform for the destination
    destination_transform = get_walker_location_from_index(spawn_points, go_to_index_location)
    destination_transform.location.z = 0.0

    # Calculate the vector between the current location and the destination
    destination_location = destination_transform.location
    movement_vector = carla.Vector3D(
        x=destination_location.x - walker_location.x,
        y=destination_location.y - walker_location.y,
        z=destination_location.z - walker_location.z
    )

    # Normalize the movement vector to get the direction
    magnitude = (movement_vector.x**2 + movement_vector.y**2 + movement_vector.z**2)**0.5
    if magnitude > 0:
        direction = carla.Vector3D(
            x=movement_vector.x / magnitude,
            y=movement_vector.y / magnitude,
            z=movement_vector.z / magnitude
        )
    else:
        direction = carla.Vector3D(0.0, 0.0, 0.0)

    # Set the walker speed and direction
    walker_control = carla.WalkerControl(direction, speed, False)
    walker.apply_control(walker_control)

    return walker
