import glob
import os
import sys

try:
    sys.path.append(glob.glob('../carla/dist/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass

import carla
import time
from DemonstrationLevelUtils import spawn_vehicle, attach_sensors_to_vehicle, spawn_walker_near_car

# min x coordinates = 0
# max x coordinates = 190
# min y coordinates = 105
# max y coordinates = 307

def main():
    try:
        # Connect to the CARLA server
        client = carla.Client('localhost', 2000)
        client.set_timeout(10.0)
        
        # Get the world
        world = client.get_world()

        # Get the blueprint library
        blueprint_library = world.get_blueprint_library()

        # Find the sensor blueprints
        walker_detection_sensor_bp = blueprint_library.find('sensor.other.walker_detection')
        v2v_broadcast_sensor_bp = blueprint_library.find('sensor.other.v2v_broadcast')

        if not walker_detection_sensor_bp or not v2v_broadcast_sensor_bp:
            print("Required sensors not found. Ensure they are added and recompiled.")
            return

        # Find the spectator (camera) actor
        spectator = world.get_spectator()
        spectator_transform = carla.Transform(
            carla.Location(x=-7.5, y=205.0, z=1.0),  # Set the desired location (x, y, z)
            carla.Rotation(pitch= 0.0, yaw=90.0, roll=0.0)  # Set the desired rotation (pitch, yaw, roll)
        )
        spectator.set_transform(spectator_transform)
        print(f"Moved spectator to: {spectator_transform.location}")
        if spectator:
            # Attach the Walker Detection Sensor to the spectator's vehicle
            vehicle_transform = spectator.get_transform()
            print("Spectator vehicle transform:", vehicle_transform)

            sensor_transform = carla.Transform(carla.Location(z=1))  # Place it above the vehicle

            walker_detection_sensor = world.spawn_actor(
                walker_detection_sensor_bp, 
                sensor_transform, 
                attach_to=spectator
            )
            print("Walker Detection Sensor attached to the spectator vehicle.")

            time.sleep(0.5)

            v2v_broadcast_sensor = world.spawn_actor(
                v2v_broadcast_sensor_bp,
                sensor_transform,
                attach_to=spectator
            )
            print("V2V Broadcast Sensor attached to the spectator vehicle.")

            walker_detection_sensor.listen(lambda _: None)
            v2v_broadcast_sensor.listen(lambda _: None)

        # Wait for 5 seconds before spawning the walker
        time.sleep(0.5)

        # Spawn extra vehicles with sensors in a loop

        while True:
            spectator_location = spectator.get_transform().location

            if  200 <= spectator_location.y <= 210 and -8 <= spectator_location.x <= -3:
                print(f"Spectator is within the target range 1: {spectator_location}")

                # Spawn a vehicle
                vehicle1 = spawn_vehicle(world, blueprint_library, -3.5, 225, 1.0, -90.0)
                walker_detection_sensor = None
                v2v_broadcast_sensor = None

                if vehicle1:
                    # Attach sensors to the vehicle
                    walker_detection_sensor, v2v_broadcast_sensor = attach_sensors_to_vehicle(
                        world, walker_detection_sensor_bp, v2v_broadcast_sensor_bp, vehicle1
                    )

                time.sleep(0.5)

                # Wait for 8 seconds
                time.sleep(8)

                # Cleanup: Destroy sensors and vehicle
                if walker_detection_sensor:
                    walker_detection_sensor.stop()
                    walker_detection_sensor.destroy()
                    print("Destroyed Walker Detection Sensor.")

                if v2v_broadcast_sensor:
                    v2v_broadcast_sensor.stop()
                    v2v_broadcast_sensor.destroy()
                    print("Destroyed V2V Broadcast Sensor.")

                if vehicle1:
                    vehicle1.destroy()
                    print("Destroyed vehicle.")

            else:
                print(f"Spectator is outside the target range 1: {spectator_location}")
                time.sleep(1)
            
            if 240 <= spectator_location.y <= 280 and -8 <= spectator_location.x <= -3:
                print(f"Spectator is within the target range 2: {spectator_location}")

                walker = spawn_walker_near_car(world, blueprint_library, spectator.get_transform(), 7, 6, 0.5)
                walker2 = spawn_walker_near_car(world, blueprint_library, spectator.get_transform(), -4, 6, 0.5)

                # Wait for 8 seconds
                time.sleep(8)

                if walker:
                    walker.destroy()
                    print("Destroyed walker.")
                if walker2:
                    walker2.destroy()
                    print("Destroyed walker2.")
                time.sleep(0.5)
            else:
                print(f"Spectator is outside the target range 2: {spectator_location}")
                time.sleep(1)

            # Check if the spectator's location is within the specified range
            if 300 <= spectator_location.y <= 310 and 70 <= spectator_location.x <= 80:
                print(f"Spectator is within the target range 3: {spectator_location}")
                # Spawn a vehicle
                vehicle = spawn_vehicle(world, blueprint_library, 174.5, 302.22, 1.0, 180.0)
                walker_detection_sensor = None
                v2v_broadcast_sensor = None

                if vehicle:
                    # Attach sensors to the vehicle
                    walker_detection_sensor, v2v_broadcast_sensor = attach_sensors_to_vehicle(
                        world, walker_detection_sensor_bp, v2v_broadcast_sensor_bp, vehicle
                    )

                time.sleep(0.5)

                # Spawn a walker
                walker = spawn_walker_near_car(world, blueprint_library, vehicle.get_transform(), -2, -3, 0.5)

                # Make the vehicle move forward
                vehicle.apply_control(carla.VehicleControl(throttle=1.0, steer=0.0))

                # Wait for 8 seconds
                time.sleep(8)

                # Cleanup: Destroy sensors and vehicle
                if walker_detection_sensor:
                    walker_detection_sensor.stop()
                    walker_detection_sensor.destroy()
                    print("Destroyed Walker Detection Sensor.")

                if v2v_broadcast_sensor:
                    v2v_broadcast_sensor.stop()
                    v2v_broadcast_sensor.destroy()
                    print("Destroyed V2V Broadcast Sensor.")

                if walker:
                    walker.destroy()
                    print("Destroyed walker.")

                if vehicle:
                    vehicle.destroy()
                    print("Destroyed vehicle.")
            else:
                print(f"Spectator is outside the target range 2: {spectator_location}")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt detected. Cleaning up...")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Cleaned up and exiting.")

if __name__ == '__main__':
    main()