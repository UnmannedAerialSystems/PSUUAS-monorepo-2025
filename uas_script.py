from MavEZ import flight_manger, flight_utils
from CameraModule import UAS_Camera
from GPSLocator import targetMapper
from ObjectDetection import lion_sight
import logging

# Configure logging
logging.basicConfig(
    filename='uas_flight_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_plan(filename):
    """
    Load the mission plan from a file.
    """
    with open(filename, 'r') as file:
        lines = file.readlines()
    mission_plan = {}
    for line in lines:
        key, value = line.split(':')
        mission_plan[key.strip()] = value.strip()
    
    mission_plan['home'] = tuple(mission_plan['home'].split(','))
    
    return mission_plan

def main():

    # =========== Initialization ===========
    flight = flight_manger.Flight()
    camera = UAS_Camera.Camera()
    mapper = targetMapper.TargetMapper()
    detection = lion_sight.LionSight()

    # ========== Mission Plan Loading ===========
    filename = input("Enter the filename of the mission plan: ")
    mission_plan = load_plan(filename)
    takeoff_mission = mission_plan['takeoff']
    landing_mission = mission_plan['landing']
    geofence_mission = mission_plan['geofence']
    detection_mission = mission_plan['detection']
    airdrop_mission = mission_plan['airdrop']
    home_coordinates = mission_plan['home']
    detect_index = mission_plan['detect_index']
    airdrop_index = mission_plan['airdrop_index']
    do_detect = mission_plan['do_detect']
    current_target = mission_plan['current_target']
    targets = mission_plan['targets']

    print("Loaded mission plan")
    logging.info(f"Loaded mission plan: {mission_plan}.")

    # ========== Preflight Checks ===========
    input("Press Enter to perform preflight checks...")
    response = flight.preflight_check(landing_mission, geofence_mission, home_coordinates)
    if response:
        print("Preflight checks failed. Exiting...")
        logging.error("Preflight checks failed.")
        return
    else:
        print("Preflight checks passed.")
        logging.info("Preflight checks passed.")

    # ========== Mission Validation ===========
    print("Validating missions...")
    flight_utils.Mission.load_mission(detection_mission)
    flight_utils.Mission.load_mission(airdrop_mission)
    flight_utils.Mission.load_mission(takeoff_mission)
    print("All missions validated.")
    logging.info("All missions validated.")

    if do_detect == 'True':
        flight.append_detect_mission(detection_mission)
        print("Appended detection mission.")
        logging.info("Appended detection mission.")

    print("Ready for takeoff")

    # ========== Takeoff Wait ===========
    print("Waiting for takeoff confirmation...")
    logging.info("Waiting for takeoff confirmation...")
    # TODO: determine channel and value
    response = flight_utils.Mission.wait_for_channel_input(7, 100)
    if response:
        print("Takeoff confirmation failed.")
        logging.error("Takeoff confirmation failed.")
        return
    else:
        print("Takeoff confirmation received.")
        logging.info("Takeoff confirmation received.")

    # ========== Takeoff ===========
    print("Taking off...")
    logging.info("Taking off...")
    response = flight.takeoff(takeoff_mission)
    if response:
        print(flight.decode_error(response))
        logging.error(f"Takeoff failed: {flight.decode_error(response)}")
        return
    else:
        print("Takeoff successful.")
        logging.info("Takeoff successful.")
    
    # ========== First Mission ===========
    print("Waiting for mission end...")
    logging.info("Waiting for mission end...")
    response = flight.wait_and_send_next_mission()
    if response:
        print(flight.decode_error(response))
        logging.error(f"Mission end failed: {flight.decode_error(response)}")
        return
    else:
        print("Next mission sent successfully.")
        logging.info("Next mission sent successfully.")
    
    # ========== Detect ===========
    if do_detect:

        fails = 0
        while fails == 0:

            # ========= Detection Zone Wait ===========
            print("Waiting to reach detection zone...")
            logging.info("Waiting to reach detection zone...")
            response = flight_utils.Mission.wait_for_waypoint_reached(detect_index, 100)
            if response:
                print(flight.decode_error(response))
                logging.error(f"Detection zone not reached: {flight.decode_error(response)}")
                return
            else:
                print("Detection zone reached.")
                logging.info("Detection zone reached.")
            
            # ========= Detection ===========
            print("Starting detection...")
            logging.info("Starting detection...")
            camera.start()
            targets = detection.detect()
            target = targets[current_target] if targets else None
            if target:
                print(f"Detected target: {target}")
                logging.info(f"Detected target: {target}")
            else:
                print("No targets detected. Repeating detect mission.")
                logging.info("No targets detected. Repeating detect mission.")
                if fails == 0:
                    fails += 1

                    # repeat detection mission
                    response = flight.append_detect_mission(detection_mission)
                    if response:
                        print(flight.decode_error(response))
                        logging.error(f"Failed to append detection mission: {flight.decode_error(response)}")
                        return
                    else:
                        print("Detection mission appended successfully.")
                        logging.info("Detection mission appended successfully.")

                    # wait for detection mission to finish
                    response = flight.wait_and_send_next_mission()
                    if response:
                        print(flight.decode_error(response))
                        logging.error(f"Detection mission failed: {flight.decode_error(response)}")
                        return
                    else:
                        print("Next mission sent successfully.")
                        logging.info("Next mission sent successfully.")
                    
                else:
                    print("Detection failed twice. Exiting...")
                    logging.error("Detection failed twice. Exiting...")
                    return
                
    # ========== Airdrop ===========
    
    if targets:
        target = targets[current_target]
        print(f"Target to airdrop: {target}")
        logging.info(f"Target to airdrop: {target}")
    else:
        print("No targets detected. Exiting...")
        logging.error("No targets detected. Exiting...")
        return

    # ========= Airdrop Target Wait ===========
    print("Waiting to reach airdrop target...")
    logging.info("Waiting to reach airdrop target...")
    response = flight_utils.Mission.wait_for_waypoint_reached(airdrop_index, 100)
    if response:
        print(flight.decode_error(response))
        logging.error(f"Airdrop target not reached: {flight.decode_error(response)}")
        return
    else:
        print("Airdrop target reached.")
        logging.info("Airdrop target reached.")

    # ========= Airdrop ===========
    print("Starting airdrop...")
    logging.info("Starting airdrop...")
    # TODO: determine servo index and value
    response = flight.controller.set_servo(airdrop_mission, 1, 2000)
    if response:
        print(flight.decode_error(response))
        logging.error(f"Airdrop failed: {flight.decode_error(response)}")
        return
    else:
        print("Airdrop successful.")
        logging.info("Airdrop successful.")
        current_target += 1
        if current_target >= len(targets):
            current_target = 0
        mission_plan['current_target'] = current_target
    




    



    








