from utils.walker_utils import get_walker_location_from_index, walker_go_to_location

class WalkerManager:
    def __init__(self, world, spawn_points):
        self.world = world
        self.spawn_points = spawn_points
        self.walkers = []  # List of walkers and their routes

    def add_walker(self, walker, route, speed):
        """
        Add a walker and its route to the manager.

        Args:
            walker (carla.Actor): The walker actor.
            route (list): List of indices representing the route.
            speed (float): Speed of the walker.
        """
        self.walkers.append({
            "walker": walker,
            "route": route,
            "current_index": 0,
            "speed": speed
        })

    def update_walkers(self):
        """
        Update all walkers in the manager, moving them along their routes.
        Destroy walkers when they reach the last point in their route.
        """
        walkers_to_remove = []  # Keep track of walkers to remove

        for walker_data in self.walkers:
            walker = walker_data["walker"]
            route = walker_data["route"]
            current_index = walker_data["current_index"]
            speed = walker_data["speed"]

            # Check if the walker has reached the current target
            if current_index < len(route):
                target_index = route[current_index]
                target_transform = get_walker_location_from_index(self.spawn_points, target_index)
                target_location = target_transform.location

                # Check distance to target
                current_location = walker.get_location()
                distance = current_location.distance(target_location)
                if distance <= 2.0:  # Deviation threshold
                    print(f"Walker reached point {target_index}")
                    walker_data["current_index"] += 1  # Move to the next point

                    # If the walker has reached the last point, mark it for removal
                    if walker_data["current_index"] >= len(route):
                        print(f"Walker has completed its route and will be destroyed.")
                        walkers_to_remove.append(walker)
                else:
                    # Move the walker toward the target
                    walker_go_to_location(walker, self.spawn_points, current_location, target_index, speed)
            else:
                # If the walker has no valid route, mark it for removal
                walkers_to_remove.append(walker)

        # Destroy walkers that have completed their routes
        for walker in walkers_to_remove:
            if walker.is_alive:
                try:
                    walker.destroy()
                    print(f"Walker {walker.id} destroyed.")
                except Exception as e:
                    print(f"Failed to destroy walker {walker.id}: {e}")

        # Remove destroyed walkers from the manager
        self.walkers = [w for w in self.walkers if w["walker"] not in walkers_to_remove]