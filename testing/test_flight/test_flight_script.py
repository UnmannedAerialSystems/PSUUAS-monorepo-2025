from MavEZ import Mission, flight_manager
from CameraTesting import camera_loop
import time

def test_flight_script():

    # Create a flight
    flight = flight_manager.Flight()

    # Perform preflight check
    response = flight.preflight_check('land.txt', 'geofence.txt')
    if response:
        print(flight.decode_error(response))
        return

    # Append detect mission
    response = flight.append_detect_mission('airdrop.txt')
    if response:
        print(flight.decode_error(response))
        return

    # Takeoff the drone
    response = flight.takeoff('takeoff.txt')
    if response:
        print(flight.decode_error(response))
        return

    # wait and run next mission
    response = flight.wait_and_send_next_mission() # detect mission
    if response:
        print(flight.decode_error(response))
        return

    # wait for detect zone to be reached
    flight.Mission.wait_for_waypoint_reached(0)

    # start camera module
    camera_loop.capture_images()

    # wait and run next mission
    response = flight.wait_and_send_next_mission() # land mission
    
    # if the land mission fails
    if response:

        # print the error
        print(flight.decode_error(response))
        
        # wait for drone to recover
        time.sleep(30)

        # retry the land mission
        flight.land_mission.send_mission()
        flight.controller.set_mode('AUTO')