'''
UAS State Actions Module

Ted Tasman
2025-03-25
PSU UAS

This module implements the actions for the UAS state machine.
'''

from MAVez.Coordinate import Coordinate
from MAVez.Mission import Mission
from MAVez.flight_manger import Flight
from logging_config import configure_logging
from LionSight2 import lion_sight_2
from UASCamera2 import UAS_camera
import time
import cv2


# MISSION STATES
PREFLIGHT = 0
TAKEOFF_WAIT = 1
TAKEOFF = 2
DETECT = 3
AIRDROP = 4
LANDING = 5
COMPLETE = 6
# TODO: add go around/circle state so waypoints don't need to be duplicated in mission file

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

    def __init__(self, connection_string='/dev/ttyACM0'):

        # Configure logging
        self.logger = configure_logging()

        # Initialize components
        self.flight = Flight(connection_string=connection_string)
        self.flight.set_logger(self.logger)

        self.camera = UAS_camera.get_camera(self.flight, self.flight.logger)  # Get real camera or emulator
        self.detection = lion_sight_2.get_ls2(logger=self.flight.logger)  # Get real detection or emulator
        
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

        self.trigger_channel = None
        self.trigger_value = None
        self.trigger_wait_time = None

        self.airdrop_altitude = 20
        self.drop_count = 0

        # Initialize states
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
        self.mission_plan['home'] = Coordinate(float(lat), float(lon), float(alt))

        self.takeoff_mission = self.mission_plan['takeoff']
        self.landing_mission = self.mission_plan['land']
        self.geofence_mission = self.mission_plan['geofence']
        self.detection_mission = self.mission_plan['detect']
        self.airdrop_mission = self.mission_plan['airdrop']
        self.home_coordinates = self.mission_plan['home']

        self.detect_index = int(self.mission_plan['detect_index'])
        self.airdrop_index = int(self.mission_plan['airdrop_index'])

        self.trigger_channel = int(self.mission_plan['trigger_channel'])
        self.trigger_value = int(self.mission_plan['trigger_value'])
        self.trigger_wait_time = int(self.mission_plan['trigger_wait_time'])

        self.airdrop_altitude = float(self.mission_plan['airdrop_altitude'])

        # set detection plan
        detection_entry = self.mission_plan['detection_entry'].split(',')
        detection_exit = self.mission_plan['detection_exit'].split(',')
        self.detection.set_plan(
            entry_coord=Coordinate(float(detection_entry[0]), float(detection_entry[1]), float(detection_entry[2])),
            exit_coord=Coordinate(float(detection_exit[0]), float(detection_exit[1]), float(detection_exit[2])),
            width=float(self.mission_plan['detection_width']),
        )

        self.next_mission_state = PREFLIGHT

        self.logger.info("[Actions] Mission plan loaded.")
    

    def append_next_mission(self):
        """
        Append the next mission to the flight plan.
        """

        if self.next_mission_state == DETECT:
            # append detection mission
            self.flight.append_mission(self.detection_mission)
            self.logger.info("Detection mission appended.")

        elif self.next_mission_state == AIRDROP:
            # append airdrop mission
            self.flight.append_airdrop_mission()
            self.logger.info("[Actions] Airdrop mission appended.")
        
        elif self.next_mission_state == LANDING:
            # append landing mission
            self.flight.append_mission(self.landing_mission)
            self.logger.info("[Actions] Landing mission appended.")
        
        elif self.next_mission_state == COMPLETE:
            # log completion
            self.logger.info("[Actions] Objective complete.")

        # takeoff wait and preflight are not missions, so do not append
        # if next mission state is not one of the above, preflight, or takeoff wait, it's invalid
        elif self.next_mission_state != PREFLIGHT and self.next_mission_state != TAKEOFF_WAIT and self.next_mission_state != TAKEOFF:
            # abort if invalid mission state
            self.logger.critical(f"Invalid mission state: {self.next_mission_state}")
            self.status = ABORT
            self.next_mission_state = LANDING

        
    def preflight_check(self):
        """
        Perform preflight checks.
        """
        # only run preflight check on first run
        if self.preflight_state == PREFLIGHT_INCOMPLETE:
            # pass preflight check to flight manager
            response = self.flight.preflight_check(self.landing_mission, self.geofence_mission, self.home_coordinates)
            if response: # any response means preflight check failed
                self.logger.critical(f"[Actions] Preflight checks failed. {response}")
                self.status = ABORT # set status to abort to end objective
                return
            
            else: # if no response, preflight check passed
                self.logger.info("[Actions] Preflight checks passed.")

                # validate missions; response is 0 if successful
                detect_response = self.validate_mission_file(self.detection_mission)
                airdrop_response = self.validate_mission_file(self.airdrop_mission)
                takeoff_response = self.validate_mission_file(self.takeoff_mission)

                # if any mission fails to load, abort
                if detect_response or airdrop_response or takeoff_response:
                    self.logger.critical(f"[Actions] Mission validation failed: Detect- {detect_response}, Airdrop- {airdrop_response}, Takeoff- {takeoff_response}")
                    self.status = ABORT
                    return
                
                self.logger.info("[Actions] All missions validated.")
                
        # if everything is ok:
        self.preflight_state = PREFLIGHT_COMPLETE
        self.next_mission_state = TAKEOFF_WAIT
        self.status = OK


    def takeoff_wait(self):
        """
        Wait for takeoff confirmation.
        """

        self.logger.info("[Actions] Waiting for takeoff confirmation...")

        # wait_for_channel_input blocks until the channel input is received or timeout
        response = self.flight.wait_for_channel_input(self.trigger_channel, self.trigger_value, wait_time=self.trigger_wait_time, value_tolerance=100) # TODO: determine channel and value
        #input("Press enter to simulate takeoff confirmation...") # TODO: remove this line and uncomment the line above
        response = 0
        # if response is not 0, takeoff confirmation failed (timeout)
        if response:
            self.logger.critical("[Actions] Takeoff confirmation failed.")
            self.status = ABORT
            self.next_mission_state = COMPLETE # still on ground, so mission is complete

        else: 
            self.logger.info("[Actions] Takeoff confirmation received.")
            self.next_mission_state = TAKEOFF # TODO: set to detect for now, but should be takeoff

    

    def takeoff(self):
        """
        Perform takeoff.
        """
        self.logger.info("[Actions] Taking off...")
        response = self.flight.takeoff(self.takeoff_mission)
        self.flight_state = FLYING # assume flying after takeoff, even if takeoff fails

        # check for response; if response is not 0, takeoff failed
        if response:
            self.logger.critical(f"[Actions] Takeoff failed: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = LANDING # must land since we are in the air

        else:
            self.logger.info("[Actions] Takeoff successful.")

            # append detection mission or airdrop mission based on detection state
            if self.detection_state == DETECT_INCOMPLETE:
                self.next_mission_state = DETECT
            else:
                self.flight.build_airdrop_mission(
                    target_coordinate=self.targets[self.drop_count],  # use first target for airdrop mission
                    airdrop_mission_file= self.airdrop_mission,  # use airdrop mission file from mission plan
                    target_index=self.airdrop_index,  # use airdrop index from mission plan
                    altitude=self.airdrop_altitude,  # set altitude for airdrop pass
                    drop_count=self.drop_count,  # set drop count to 0 for first airdrop
                )
                self.next_mission_state = AIRDROP
    

    def detect(self):
        """
        Perform detection
        """
        # wait and send detection mission
        self.logger.info("[Actions] Waiting to send detection mission...")
        self.flight.detect_mission.load_mission_from_file(self.detection_mission)
        self.flight.wait_and_send_next_mission()


        # wait to reach detection zone
        self.logger.info("[Actions] Waiting to reach detection zone...")

        # wait_for_waypoint_reached blocks until the specified waypoint is reached or timeout
        response = self.flight.wait_for_waypoint_reached(self.detect_index, 100)

        # check for response; if response is not 0, detection zone not reached
        if response:
            self.logger.critical(f"[Actions] Detection zone not reached: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = LANDING
            return
        
        self.logger.info("[Actions] Starting detection...")

        # take photos
        self.camera.capture_images(20, 0)
        
        # perform detection
        self.detection.images = self.camera.images
        targets = self.detection.detect()

        # check for detection results
        if targets: # for successful detection

            self.logger.info(f"[Actions] Detected target: {targets}")
            self.targets = targets

            self.flight.build_airdrop_mission(
                target_coordinate=self.targets[self.drop_count],  # use first target for airdrop mission
                airdrop_mission_file= self.airdrop_mission,  # use airdrop mission file from mission plan
                target_index=self.airdrop_index,  # use airdrop index from mission plan
                altitude=self.airdrop_altitude,  # set altitude for airdrop pass
                drop_count=self.drop_count,  # set drop count to 0 for first airdrop
            )

            self.detection_state = DETECT_COMPLETE
            self.next_mission_state = AIRDROP

        else: # for failed detection

            self.logger.warning("[Actions] No targets detected.")

            # increment detection attempts to prevent infinite loop
            self.detect_attempts += 1
            self.detection_state = DETECT_FAIL
            
            # if max attempts reached, abort
            if self.detect_attempts >= self.max_detect_attempts:
                self.logger.critical("[Actions] Max detection attempts reached. Aborting...")
                self.status = ABORT
                self.mission_state = LANDING
                return
            
            # if not, retry detection (go around again)
            else:
                self.logger.info("[Actions] Retrying detection...")
                self.detection_state = DETECT_INCOMPLETE # fall back to incomplete for proper retry
                self.next_mission_state = DETECT
                return
        

    def airdrop(self):
        '''
        Perform airdrop
        '''
        print("===============AIRDROPPING===============")
        # wait and send airdrop mission
        self.logger.info("[Actions] Waiting to send airdrop mission...")
        self.flight.wait_and_send_next_mission()
        

        # # targets must exist to perform airdrop
        # if not self.targets:
        #     self.logger.error("[Actions] No targets detected. Cannot perform airdrop.")
            
        #     # we can run detection if we have not reached max attempts
        #     if self.detect_attempts < self.max_detect_attempts:
        #         self.logger.info("[Actions] Attempting to detect again...")
        #         self.next_mission_state = DETECT
        #         return
        #     else:
        #         self.logger.critical("[Actions] Max detection attempts reached. Aborting...")
        #         self.status = ABORT
        #         self.mission_state = LANDING
        #         return
        
        # # wait to reach airdrop zone
        # self.logger.info("[Actions] Waiting to reach airdrop zone...")

        # # wait_for_waypoint_reached blocks until the specified waypoint is reached or timeout
        # response = self.flight.wait_for_waypoint_reached(self.airdrop_index, 100)

        # # check for response; if response is not 0, airdrop zone not reached
        # if response:
        #     self.logger.critical(f"[Actions] Airdrop zone not reached: {self.flight.decode_error(response)}")
        #     self.status = ABORT
        #     self.mission_state = LANDING
        #     return
        
        # else:
        
        #     # perform airdrop
        #     self.logger.info("[Actions] Triggering airdrop servo...")
        #     self.flight.set_servo(self.airdrop_servo, self.airdrop_value_open) 
        #     time.sleep(2)
        #     self.flight.set_servo(self.airdrop_servo, self.airdrop_value_close)
        #     self.logger.info("[Actions] Airdrop successful.")
            
        #     self.current_target += 1
        #     self.payload_state = PAYLOAD_RELEASED

        #     # check if all targets have been airdropped
        #     if self.current_target >= len(self.targets):
        #         # if so, mission is complete
        #         self.logger.info("[Actions] All targets airdropped. Mission complete.")
        #         self.completion_state = AIRDROPS_COMPLETE 
            
        #     # land no matter what after airdrop
        #     self.next_mission_state = LANDING

        # TODO: receive airdrop confirmation from drop script

        # self.logger.info(f"[Actions] Airdrop {self.drop_count + 1} successful.")

        self.drop_count += 1
        if self.drop_count % 2 == 0: # all even drops need landing
            self.logger.info(f"[Actions] Payload {self.drop_count} away. Landing now.")
            self.next_mission_state = LANDING
        else: # odd drops can continue to next mission
            self.logger.info(f"[Actions] Payload {self.drop_count} away. Continuing to next airdrop.")
            self.flight.build_airdrop_mission(
                target_coordinate=self.targets[self.drop_count],  # use first target for airdrop mission
                airdrop_mission_file= self.airdrop_mission,  # use airdrop mission file from mission plan
                target_index=self.airdrop_index,  # use airdrop index from mission plan
                altitude=self.airdrop_altitude,  # set altitude for airdrop pass
                drop_count=self.drop_count,  # increment drop count for next airdrop
            )
            self.next_mission_state = AIRDROP # continue to airdrop next target


    def land(self):
        """
        Perform landing.
        """
        # wait and send landing mission
        self.logger.info("[Actions] Waiting to send landing mission...")
        self.flight.wait_and_send_next_mission()

        # wait to be landed
        self.logger.info("[Actions] Waiting for land confirmation...")
        # wait_for_landed blocks until the vehicle is landed or timeout
        response = self.flight.wait_for_landed(200)

        # check for response; if response is not 0, landing failed
        if response:
            self.logger.critical(f"[Actions] Landing failed: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = COMPLETE # set to complete so it doesn't keep trying to land
            return
        
        self.logger.info("[Actions] Landing successful.")

        self.logger.info("[Actions] Disarming")
        response = self.flight.disarm(force=True)
        if response:
            self.logger.critical(f"[Actions] Failed to disarm: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = COMPLETE
            return
        
        self.logger.info("[Actions] Setting mode to manual")
        response = self.flight.set_mode("MANUAL")
        if response:
            self.logger.critical(f"[Actions] Failed to set mode to MANUAL: {self.flight.decode_error(response)}")
            self.status = ABORT
            self.next_mission_state = COMPLETE
            return
        
        if self.drop_count == 4:
            self.logger.info("[Actions] All payloads airdropped. Mission complete.")
            self.next_mission_state = COMPLETE
            return

        # jump ahead to complete mission TODO: re-enable this for re-takeoff
        self.logger.info("Jumping to next mission item...")
        self.flight.jump_to_next_mission_item()

        self.flight_state = IDLE
        self.next_mission_state = TAKEOFF_WAIT # TODO: set to preflight for re-takeoff
        

    def validate_mission_file(self, filename):
        '''
            Validate a mission from a file.
            filename: str
            start: int
            end: int
            returns:
                0 if the mission was loaded successfully
                201 if the file was not found
                202 if the file was empty
        '''
        FILE_NOT_FOUND = 501
        FILE_EMPTY = 502

        try:
            with open(filename, 'r') as file:
                lines = file.readlines()
        except FileNotFoundError:
            if self.logger:
                self.logger.error(f'[Actions] File {filename} not found')
            return FILE_NOT_FOUND

        if len(lines) == 0:
            if self.logger:
                self.logger.error(f'[Actions] File {filename} is empty')
            return FILE_EMPTY

        for line in lines[1:]:
            # skip empty lines
            if line == '\n':
                continue

            parts = line.strip().split('\t')
            if len(parts) != 12:
                if self.logger:
                    self.logger.error(f'[Actions] Invalid line in file {filename}: {line}')
                return FILE_EMPTY
        
        if self.logger:
            self.logger.info(f'[Actions] Mission file {filename} is valid')
        return 0
        


def main():

    op = Operation(connection_string='tcp:127.0.0.1:5762')
    op.load_plan('./testing/mission_plan_sample.txt')

if __name__ == "__main__":
    main()



    





                                                                                                    





        




            

    





