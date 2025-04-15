import glob
import os
import sys
import random

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla

def spawn_vehicle(world, bp_lib, model="vehicle.tesla.model3", transform=None):
    bp = bp_lib.find(model)
    if not bp:
        raise ValueError(f"Vehicle model '{model}' not found in blueprint library.")
    
    if transform is None:
        transform = random.choice(world.get_map().get_spawn_points())
    
    vehicle = world.spawn_actor(bp, transform)
    if not vehicle:
        raise RuntimeError(f"Failed to spawn vehicle '{model}' at {transform.location}.")
    return vehicle

def spawn_walker(world, bp_lib, transform):
    bp = bp_lib.find('walker.pedestrian.0001')
    if not bp:
        raise ValueError("Walker blueprint not found in blueprint library.")
    
    if transform is None:
        transform = random.choice(world.get_map().get_spawn_points())
    
    walker = world.spawn_actor(bp, transform)
    if not walker:
        raise RuntimeError(f"Failed to spawn walker at {transform.location}.")
    return walker

def set_autopilot(vehicle, enable=True):
    vehicle.set_autopilot(enable)