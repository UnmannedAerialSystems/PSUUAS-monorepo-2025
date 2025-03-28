from MavEZ import flight_manger, flight_utils
from CameraModule import UAS_Camera
from GPSLocator import targetMapper
from ObjectDetection import lion_sight

def main():

    # Initialize the modules
    flight = flight_manger.Flight()
    camera = UAS_Camera.Camera()
    mapper = targetMapper.TargetMapper()
    detection = lion_sight.LionSight()

    # Load the missions
    landing_mission = input("Enter the landing mission filename: ")
    geofence_mission = input("Enter the geofence mission filename: ")
    detection_mission = input("Enter the detection mission filename: ")
    airdrop_mission = input("Enter the airdrop mission filename: ")
    takeoff_mission = input("Enter the takeoff mission filename: ")
    home_coordinates = input("Enter home coordinates (lat, lon, alt): ")

    # Perform preflight checks
    input("Press Enter to perform preflight checks...")
    response = flight.preflight_check(landing_mission, geofence_mission, home_coordinates)
    if response:
        print("Preflight checks failed. Exiting...")
        return
    else:
        print("Preflight checks passed.")

    print("Validating missions...")
    flight_utils.Mission.load_mission(detection_mission)
    flight.append_detect_mission(detection_mission)
    flight_utils.Mission.load_mission(airdrop_mission)
    flight_utils.Mission.load_mission(takeoff_mission)
    print("All missions validated.")

    # Takeoff
    confirm = None
    while confirm != "takeoff":
        confirm = input("Confirm takeoff by typing 'takeoff' or 'abort' to cancel: ").lower()
        if confirm == "abort":
            print("Takeoff aborted.")
            return
        elif confirm != "takeoff":
            print("Invalid input. Please type 'takeoff' to proceed.")
    

    print("Taking off...")
    response = flight.takeoff(takeoff_mission)
    if response:
        print(flight.decode_error(response))
        return
    else:
        print("Takeoff successful.")
    
    print("Waiting for mission end...")
    response = flight.wait_and_send_next_mission()
    if response:
        print(flight.decode_error(response))
        return
    else:
        print("Next mission sent successfully.")
    
    # wait for detection zone to be reached
    
    








