'''
UAS State Actions Module

Ted Tasman
2025-03-25
PSU UAS

This module implements the actions for the UAS state machine.
'''
import sys
import os
# Add MavEZ directory to the system path
mavez_path = os.path.join(os.path.dirname(__file__), 'MavEZ')
if mavez_path not in sys.path:
    sys.path.append(mavez_path)

from MavEZ import Mission, flight_manger, Coordinate
from CameraModule import camera_emulator as UAS_Camera
#from GPSLocator import targetMapper
from ObjectDetection import lion_sight_emulator as lion_sight
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

# STATUS STATES
OK = 0
ABORT = 1

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
        #self.camera = UAS_Camera.Camera()
        #self.mapper = targetMapper.TargetMapper()
        #self.detection = lion_sight.LionSight()
        
        # Initialize mission parameters
        self.mission_plan = None
        self.detect_index = None
        self.airdrop_index = None
        self.home_coordinates = None
        self.takeoff_mission = None
        self.landing_mission = None
        self.geofence_mission = None
        self.detection_mission = None
        self.airdrop_mission = None

        # Initialize states
        self.mission_state = PREFLIGHT
        self.next_mission_state = None
        self.status = None
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
            # skip empty lines
            if line == '\n':
                continue
            # extract key and value from line and add to mission plan
            key, value = line.split(':')
            self.mission_plan[key.strip()] = value.strip()
        
        # convert home coordinates to Coordinate object
        lat, lon, alt = self.mission_plan['home'].split(',')
        self.mission_plan['home'] = Coordinate.Coordinate(float(lat), float(lon), float(alt))

        
        self.takeoff_mission = self.mission_plan['takeoff']
        self.landing_mission = self.mission_plan['land']
        self.geofence_mission = self.mission_plan['geofence']
        self.detection_mission = self.mission_plan['detect']
        self.airdrop_mission = self.mission_plan['airdrop']
        self.home_coordinates = self.mission_plan['home']
        self.detect_index = int(self.mission_plan['detect_index'])
        self.airdrop_index = int(self.mission_plan['airdrop_index'])

        self.next_mission_state = PREFLIGHT

        logging.info("Mission plan loaded.")
        print("Mission plan loaded.")
    

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
            # log completion
            logging.info("Objective complete.")
            print("Objective complete.")

        # takeoff wait and preflight are not missions, so do not append
        # if next mission state is not one of the above, preflight, or takeoff wait, it's invalid
        elif self.next_mission_state != PREFLIGHT and self.next_mission_state != TAKEOFF_WAIT:
            # abort if invalid mission state
            logging.critical(f"Invalid mission state: {self.next_mission_state}")
            print(f"Invalid mission state: {self.next_mission_state}")
            self.status = ABORT
            self.next_mission_state = LANDING

        
    def preflight_check(self):
        """
        Perform preflight checks.
        """
        # pass preflight check to flight manager
        response = self.flight.preflight_check(self.landing_mission, self.geofence_mission, self.home_coordinates)
        if response: # any response means preflight check failed
            print("Preflight checks failed. Aborting...")
            logging.critical(f"Preflight checks failed. {response}")
            self.status = ABORT # set status to abort to end objective
            return
        
        else: # if no response, preflight check passed
            print("Preflight checks passed.")
            logging.info("Preflight checks passed.")

            # validate missions; response is 0 if successful
            detect_response = Mission.Mission.validate_mission_file(self.detection_mission) # this syntax is horrible python needs export default or something
            airdrop_response = Mission.Mission.validate_mission_file(self.airdrop_mission)
            takeoff_response = Mission.Mission.validate_mission_file(self.takeoff_mission)

            # if any mission fails to load, abort
            if detect_response or airdrop_response or takeoff_response:
                print("Mission validation failed.")
                logging.critical(f"Mission validation failed: Detect- {detect_response}, Airdrop- {airdrop_response}, Takeoff- {takeoff_response}")
                self.status = ABORT
                return
            
            print("All missions validated.")
            logging.info("All missions validated.")
            
            # if everything is ok:
            self.preflight_state = PREFLIGHT_COMPLETE
            self.next_mission_state = TAKEOFF_WAIT
            self.status = OK


    def takeoff_wait(self):
        """
        Wait for takeoff confirmation.
        """
        # wait for takeoff confirmation from remote control
        print("Waiting for takeoff confirmation...")
        logging.info("Waiting for takeoff confirmation...")

        # wait_for_channel_input blocks until the channel input is received or timeout
        #response = Mission.Mission.wait_for_channel_input(7, 100) # TODO: determine channel and value
        response = input("Press Enter to confirm takeoff...") # TODO: replace with channel input
        
        # if response is not 0, takeoff confirmation failed (timeout)
        if response:
            print("Takeoff confirmation failed.")
            logging.critical("Takeoff confirmation failed.")
            self.status = ABORT
            self.next_mission_state = COMPLETE # still on ground, so mission is complete

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
        self.flight_state = FLYING # assume flying after takeoff, even if takeoff fails

        # check for response; if response is not 0, takeoff failed
        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Takeoff failed: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = LANDING # must land since we are in the air

        else:
            print("Takeoff successful.")
            logging.info("Takeoff successful.")

            # append detection mission or airdrop mission based on detection state
            if self.detection_state == DETECT_INCOMPLETE:
                self.next_mission_state = DETECT
            else:
                self.next_mission_state = AIRDROP
    

    def detect(self):
        """
        Perform detection
        """

        # wait and send detection mission
        print("Waiting to send detection mission...")
        logging.info("Waiting to send detection mission...")
        self.flight.wait_and_send_next_mission()

        # wait to reach detection zone
        print("Waiting to reach detection zone...")
        logging.info("Waiting to reach detection zone...")

        # wait_for_waypoint_reached blocks until the specified waypoint is reached or timeout
        response = self.flight.wait_for_waypoint_reached(self.detect_index, 100)

        # check for response; if response is not 0, detection zone not reached
        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Detection zone not reached: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = LANDING
            return
        
        # if no response, detection zone reached
        else:
            print("Detection zone reached.")
            logging.info("Detection zone reached.")
        
        print("Starting detection...")
        logging.info("Starting detection...")

        # take photos
        #self.camera.start()

        # returns detection results if successful
        #targets = self.detection.detect()
        targets = [1, 2, 3] # TODO: replace with actual detection results

        # check for detection results
        if targets: # for successful detection

            print(f"Detected target: {targets}")
            logging.info(f"Detected target: {targets}")
            self.targets = targets
            self.detection_state = DETECT_COMPLETE
            self.next_mission_state = AIRDROP

        else: # for failed detection

            print("No targets detected.")
            logging.warning("No targets detected.")

            # increment detection attempts to prevent infinite loop
            self.detect_attempts += 1
            self.detection_state = DETECT_FAIL
            
            # if max attempts reached, abort
            if self.detect_attempts >= self.max_detect_attempts:
                print("Max detection attempts reached. Aborting...")
                logging.critical("Max detection attempts reached. Aborting...")
                self.status = ABORT
                self.mission_state = LANDING
                return
            
            # if not, retry detection (go around again)
            else:
                print("Retrying detection...")
                logging.info("Retrying detection...")
                self.detection_state = DETECT_INCOMPLETE # fall back to incomplete for proper retry
                self.next_mission_state = DETECT
                return
    

    def airdrop(self):
        '''
        Perform airdrop
        '''
        # wait and send airdrop mission
        print("Waiting to send airdrop mission...")
        logging.info("Waiting to send airdrop mission...")
        self.flight.wait_and_send_next_mission()

        # targets must exist to perform airdrop
        if not self.targets:
            print("No targets detected. Cannot perform airdrop.")
            logging.error("No targets detected. Cannot perform airdrop.")
            
            # we can run detection if we have not reached max attempts
            if self.detect_attempts < self.max_detect_attempts:
                print("Attempting to detect again...")
                logging.info("Attempting to detect again...")
                self.next_mission_state = DETECT
                return
            else:
                print("Max detection attempts reached. Aborting...")
                logging.critical("Max detection attempts reached. Aborting...")
                self.status = ABORT
                self.mission_state = LANDING
                return
        
        # wait to reach airdrop zone
        print("Waiting to reach airdrop zone...")
        logging.info("Waiting to reach airdrop zone...")

        # wait_for_waypoint_reached blocks until the specified waypoint is reached or timeout
        response = self.flight.wait_for_waypoint_reached(self.airdrop_index, 100)

        # check for response; if response is not 0, airdrop zone not reached
        if response:
            print(self.flight.decode_error(response))
            logging.critical(f"Airdrop zone not reached: {self.flight.decode_error(response)}")
            self.status = ABORT
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


def main():

    op = Operation()
    op.load_plan('./testing/mission_plan_sample.txt')

if __name__ == "__main__":
    main()



    





                                                                                                    





        




            

    





