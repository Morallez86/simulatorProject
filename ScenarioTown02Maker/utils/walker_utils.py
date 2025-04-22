import carla

# Custom index lists for sidewalk zones
LEFT_SIDEWALK = [27, 94, 25, 29, 31, 86, 33, 35, 60, 70, 58, 84, 62, 64, 66, 68, 50, 48, 88, 54, 39, 37, 91, 43, 45, 47]
RIGHT_SIDEWALK = [28, 95, 26, 30, 32, 34, 36, 61, 71, 59, 63, 83, 65, 67, 69, 57, 49, 89, 55, 38, 40, 92, 42, 90, 44, 46]
TOP_SIDEWALK = [23, 21, 19, 13, 15, 80, 82, 76, 78, 72, 74, 11, 9, 85, 7, 5, 99, 97, 3]
BOTTOM_SIDEWALK = [24, 22, 18, 14, 93, 16, 81, 0, 77, 79, 73, 75, 12, 10, 8, 6, 96, 100, 98, 4]
UNAVAILABLE_SPAWN_INDEXES = [1, 2, 17, 20, 41, 42, 51, 52, 53, 56, 87]

def get_walker_offset_for_index(index):
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
    if index >= len(spawn_points):
        raise IndexError("Invalid spawn point index.")

    transform = spawn_points[index]
    offset = get_walker_offset_for_index(index)

    new_location = carla.Location( # type: ignore
        x=transform.location.x + offset[0],
        y=transform.location.y + offset[1],
        z=transform.location.z + offset[2],
    )

    return carla.Transform(new_location, transform.rotation) # type: ignore

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
