'''
UAS State Actions Module
Ted Tasman
Date: 2025-03-25
This module implements the actions for the UAS state machine.
'''

from MavEZ import Mission, flight_manger
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

# MISSION STATES
PREFLIGHT = 0
TAKEOFF_WAIT = 1
TAKEOFF = 2
DETECT = 3
AIRDROP = 4
LANDING = 5
COMPLETE = 6

# FLIGHT STATES
IDLE = 0
FLYING = 1
ABORT = 2

# PREFLIGHT STATES
PREFLIGHT_INCOMPLETE = 0
PREFLIGHT_COMPLETE = 1

# DETECTION STATES
DETECT_INCOMPLETE = 0
DETECT_COMPLETE = 1
DETECT_FAIL = 2

# PAYLOAD STATES
PAYLOAD_PRESENT = 0
PAYLOAD_RELEASED = 1

# COMPLETION STATES
AIRDROPS_INCOMPLETE = 0
AIRDROPS_COMPLETE = 1



# ============== Parameters =================
MAX_DETECT_ATTEMPTS = 2


class Operation:

    def __init__(self):
        # Initialize components
        self.flight = flight_manger.Flight()
        self.camera = UAS_Camera.Camera()
        self.mapper = targetMapper.TargetMapper()
        self.detection = lion_sight.LionSight()
        
        # Initialize mission parameters
        self.mission_plan = None
        self.current_target = None
        self.targets = None
        self.detect_index = None
        self.airdrop_index = None
        self.home_coordinates = None
        self.takeoff_mission = None
        self.landing_mission = None
        self.geofence_mission = None
        self.detection_mission = None
        self.airdrop_mission = None

        # Initialize states
        self.mission_state = None
        self.next_mission_state = None
        self.flight_state = IDLE
        self.detection_state = DETECT_INCOMPLETE
        self.payload_state = PAYLOAD_PRESENT
        self.preflight_state = PREFLIGHT_INCOMPLETE
        self.airdrop_state = AIRDROPS_INCOMPLETE
        
        # Initialize mission data
        self.detect_attempts = 0
        self.max_detect_attempts = MAX_DETECT_ATTEMPTS - 1
        self.targets = []
        self.current_target = 0



    def load_plan(self, filename):
        """
        Load the mission plan from a file.
        """
        with open(filename, 'r') as file:
            lines = file.readlines()
        self.mission_plan = {}
        for line in lines:
            key, value = line.split(':')
            self.mission_plan[key.strip()] = value.strip()
        
        self.mission_plan['home'] = tuple(self.mission_plan['home'].split(','))
        
        self.takeoff_mission = self.mission_plan['takeoff']
        self.landing_mission = self.mission_plan['landing']
        self.geofence_mission = self.mission_plan['geofence']
        self.detection_mission = self.mission_plan['detection']
        self.airdrop_mission = self.mission_plan['airdrop']
        self.home_coordinates = self.mission_plan['home']
        self.detect_index = self.mission_plan['detect_index']
        self.airdrop_index = self.mission_plan['airdrop_index']
        self.current_target = self.mission_plan['current_target']
        self.targets = self.mission_plan['targets']

        self.next_mission_state = PREFLIGHT
    

    def append_next_mission(self):
        """
        Append the next mission to the flight plan.
        """
        
        if self.next_mission_state == TAKEOFF:
            # append takeoff mission
            self.flight.append_mission(self.takeoff_mission)
            print("Takeoff mission appended.")
            logging.info("Takeoff mission appended.")


        elif self.next_mission_state == DETECT:
            # append detection mission
            self.flight.append_mission(self.detection_mission)
            print("Detection mission appended.")
            logging.info("Detection mission appended.")

        elif self.next_mission_state == AIRDROP:
            # append airdrop mission
            self.flight.append_mission(self.airdrop_mission)
            print("Airdrop mission appended.")
            logging.info("Airdrop mission appended.")
        
        elif self.next_mission_state == LANDING:
            # append landing mission
            self.flight.append_mission(self.landing_mission)
            print("Landing mission appended.")
            logging.info("Landing mission appended.")
        
        elif self.next_mission_state == COMPLETE:
            # append geofence mission
            self.flight.append_mission(self.geofence_mission)
            print("Geofence mission appended.")
            logging.info("Geofence mission appended.")
        else:
            logging.critical("Invalid mission state.")
            print("Invalid mission state.")
            self.flight_state = ABORT
            self.next_mission_state = LANDING

        

    def preflight_check(self):
        """
        Perform preflight checks.
        """
        response = self.flight.preflight_check(self.landing_mission, self.geofence_mission, self.home_coordinates)
        if response:
            print("Preflight checks failed. Aborting...")
            logging.critical("Preflight checks failed.")
            self.flight_state = ABORT
            self.next_mission_state = LANDING
            return
        
        else:
            print("Preflight checks passed.")
            logging.info("Preflight checks passed.")

            Mission.Mission.load_mission(self.detection_mission) # this syntax is horrible python needs export default or something
            Mission.Mission.load_mission(self.airdrop_mission)
            Mission.Mission.load_mission(self.takeoff_mission)
            print("All missions validated.")
            logging.info("All missions validated.")
            
            self.preflight_state = PREFLIGHT_COMPLETE
            self.next_mission_state = TAKEOFF_WAIT
    

    def takeoff_wait(self):
        """
        Wait for takeoff confirmation.
        """
        print("Waiting for takeoff confirmation...")
        logging.info("Waiting for takeoff confirmation...")
        response = Mission.Mission.wait_for_channel_input(7, 100) # TODO: determine channel and value

        if response:
            print("Takeoff confirmation failed.")
            logging.critical("Takeoff confirmation failed.")
            self.flight_state = ABORT
            self.next_mission_state = LANDING

        else:
            print("Takeoff confirmation received.")
            logging.info("Takeoff confirmation received.")
            self.next_mission_state = TAKEOFF

    

    def takeoff(self):
        """
        Perform takeoff.
        """
        print("Taking off...")
        logging.info("Taking off...")
        response = self.flight.takeoff(self.takeoff_mission)

        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Takeoff failed: {self.flight.decode_error(response)}")
            self.flight_state = ABORT
            self.next_mission_state = LANDING
        else:
            print("Takeoff successful.")
            logging.info("Takeoff successful.")
            self.flight_state = FLYING

            # check if detection is required
            if self.do_detect == DETECT_INCOMPLETE:
                print("Detection mission appended.")
                logging.info("Detection mission appended.")
                self.mission_state = DETECT
            else:
                
                self.mission_state = DETECT
    

    def detect(self):
        """
        Perform detection
        """
        # wait to reach detection zone
        print("Waiting to reach detection zone...")
        logging.info("Waiting to reach detection zone...")
        response = Mission.Mission.wait_for_waypoint_reached(self.detect_index, 100)

        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Detection zone not reached: {self.flight.decode_error(response)}")
            self.flight_state = ABORT
            self.mission_state = LANDING
            return
        else:
            print("Detection zone reached.")
            logging.info("Detection zone reached.")
        
        print("Starting detection...")
        logging.info("Starting detection...")

        # perform detection
        self.camera.start()
        targets = self.detection.detect()

        # check for detection results
        if targets: # for successful detection

            print(f"Detected target: {targets}")
            logging.info(f"Detected target: {targets}")
            self.targets = targets
            self.detection_state = DETECT_COMPLETE

        else: # for failed detection

            print("No targets detected.")
            logging.warning("No targets detected.")
            self.detect_attempts += 1
            self.detection_state = DETECT_FAIL
            
            # if max attempts reached, abort
            if self.detect_attempts >= self.max_detect_attempts:
                print("Max detection attempts reached. Aborting...")
                logging.critical("Max detection attempts reached. Aborting...")
                self.flight_state = ABORT
                self.mission_state = LANDING
                return
            
            # if not, retry detection
            else:
                print("Retrying detection...")
                logging.info("Retrying detection...")
                self.detection_state = DETECT_INCOMPLETE
                self.mission_state = DETECT
                return
    

    def airdrop(self):
        '''
        Perform airdrop
        '''
        # verify that targets exist
        if not self.targets:
            print("No targets detected. Cannot perform airdrop.")
            logging.error("No targets detected. Cannot perform airdrop.")
            
            # check if detect is possible
            if self.detect_attempts < self.max_detect_attempts:
                print("Attempting to detect again...")
                logging.info("Attempting to detect again...")
                self.mission_state = DETECT
                return
            else:
                print("Max detection attempts reached. Aborting...")
                logging.critical("Max detection attempts reached. Aborting...")
                self.flight_state = ABORT
                self.mission_state = LANDING
                return
        
        # wait to reach airdrop zone
        print("Waiting to reach airdrop zone...")
        logging.info("Waiting to reach airdrop zone...")
        response = Mission.Mission.wait_for_waypoint_reached(self.airdrop_index, 100)

        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Airdrop zone not reached: {self.flight.decode_error(response)}")
            self.flight_state = ABORT
            self.mission_state = LANDING
            return
        else:
            print("Airdrop zone reached.")
            logging.info("Airdrop zone reached.")
        
            # perform airdrop
            self.flight.controller.set_servo(self.airdrop_mission, 1, 2000) # TODO: determine servo index and value
            print("Airdrop successful.")
            logging.info("Airdrop successful.")
            
            self.current_target += 1
            self.payload_state = PAYLOAD_RELEASED

            # check if all targets have been airdropped
            if self.current_target >= len(self.targets):
                # if so, mission is complete
                print("All targets airdropped. Mission complete.")
                logging.info("All targets airdropped. Mission complete.")
                self.completion_state = AIRDROPS_COMPLETE 
                self.mission_state = LANDING
    

    def land(self):
        """
        Perform landing.
        """
        # wait 



    





                                                                                                    





        




            

    





