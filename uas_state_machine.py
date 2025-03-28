'''
UAS State Machine
Author: Ted Tasman
Date: 2025-03-25
This script implements a state machine for an Unmanned Aerial System (UAS) operation.
'''

import uas_state_actions
import logging

# Configure logging
logging.basicConfig(
    filename='uas_state_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# MISSION STATES
PREFLIGHT = uas_state_actions.PREFLIGHT
TAKEOFF_WAIT = uas_state_actions.TAKEOFF_WAIT
TAKEOFF = uas_state_actions.TAKEOFF
DETECT = uas_state_actions.DETECT
AIRDROP = uas_state_actions.AIRDROP
LANDING = uas_state_actions.LANDING
COMPLETE = uas_state_actions.COMPLETE

# FLIGHT STATES
IDLE = uas_state_actions.IDLE
FLYING = uas_state_actions.FLYING
ABORT = uas_state_actions.ABORT

# PREFLIGHT STATES
PREFLIGHT_INCOMPLETE = uas_state_actions.PREFLIGHT_INCOMPLETE
PREFLIGHT_COMPLETE = uas_state_actions.PREFLIGHT_COMPLETE
# DETECTION STATES
DETECT_INCOMPLETE = uas_state_actions.DETECT_INCOMPLETE
DETECT_COMPLETE = uas_state_actions.DETECT_COMPLETE
DETECT_FAIL = uas_state_actions.DETECT_FAIL
# PAYLOAD STATES
PAYLOAD_PRESENT = uas_state_actions.PAYLOAD_PRESENT
PAYLOAD_RELEASED = uas_state_actions.PAYLOAD_RELEASED
# COMPLETION STATES
AIRDROPS_INCOMPLETE = uas_state_actions.AIRDROPS_INCOMPLETE
AIRDROPS_COMPLETE = uas_state_actions.AIRDROPS_COMPLETE


def main():

    # Initialize operation
    operation = uas_state_actions.Operation()

    # Load mission plan
    operation.load_plan('mission_plan.txt')

    while operation.next_mission_state != COMPLETE:                                             # while mission is incomplete,

        # ==== 0 - PREFLIGHT ====
        if operation.next_mission_state == PREFLIGHT:                                               # if preflight check is required,
            logging.info("PREFLIGHT")
            operation.preflight_check()                                                                 # perform preflight check,
            if operation.flight_state == ABORT:                                                         # and if abort is required,
                logging.critical("ABORT")
                operation.next_mission_state = COMPLETE                                                     # set next mission state to complete and stop.
            else:                                                                                       # or if preflight check is complete,
                operation.next_mission_state = TAKEOFF_WAIT                                                 # set next mission state to takeoff wait and repeat.
        # ==== 1 - TAKEOFF_WAIT ====
        elif operation.next_mission_state == TAKEOFF_WAIT:                                          # or if waiting for takeoff confirmation,
            logging.info("TAKEOFF_WAIT")
            operation.takeoff_wait()                                                                    # wait for takeoff confirmation,
            if operation.flight_state == ABORT:                                                         # and if abort is required,
                logging.critical("ABORT")
                operation.next_mission_state = COMPLETE                                                     # set next mission state to complete and stop.
            else:                                                                                       # or if takeoff confirmation is received,
                operation.next_mission_state = TAKEOFF                                                     # set next mission state to takeoff and repeat.

        # ==== 2 - TAKEOFF ====
        elif operation.next_mission_state == TAKEOFF:                                               # or if takeoff is required,
            logging.info("TAKEOFF")
            if operation.detection_state == DETECT_INCOMPLETE:                                          # and if detection is incomplete,
                operation.next_mission_state = DETECT                                                       # append detection mission and repeat.
            else:                                                                                       # or if detection is complete, 
                operation.next_mission_state = AIRDROP                                                      # append airdrop mission and repeat.

        # ==== 3 - DETECT ====
        elif operation.next_mission_state == DETECT:                                                # or if detection is required,
            logging.info("DETECT")
            operation.detect()                                                                          # perform detection,
            if operation.detection_state == DETECT_COMPLETE:                                            # and if detection is complete,
                operation.next_mission_state = AIRDROP                                                      # append airdrop mission and repeat.
            elif operation.detect_attempts >= operation.max_detect_attempts:                            # if detection max is reached,
                    logging.critical("Detection failed, aborting")
                    operation.flight_state = ABORT                                                          # abort,
                    operation.next_mission_state = LANDING                                                  # and append landing mission and repeat.
            else:                                                                                       # or if detection is incomplete,
                operation.next_mission_state = DETECT                                                       # append detection mission and repeat.
        
        # ==== 4 - AIRDROP ====
        elif operation.next_mission_state == AIRDROP:                                               # or if airdrop is required,
            logging.info("AIRDROP")
            operation.airdrop()                                                                         # perform airdrop,
            operation.next_mission_state = LANDING                                                      # and append landing mission and repeat.

        # ==== 5 - LANDING ====    
        elif operation.next_mission_state == LANDING:                                               # or if landing is required,
            logging.info("LANDING")
            operation.land()                                                                            # perform landing,
            if operation.completion_state == AIRDROPS_COMPLETE or operation.flight_state == ABORT:              # and if mission is complete or if abort is required
                logging.info("Mission terminated")
                operation.next_mission_state = COMPLETE                                                             # set next mission state to complete and stop.
            else:                                                                                               # or if mission is not complete,   
                operation.next_mission_state = PREFLIGHT                                                            # set next mission state to preflight and repeat.
        
        # ==== STATE MACHINE ERROR ====
        else:                                                                                       # otherwise, 
            logging.error("State machine error, aborting")                                              # something is very probably very wrong.
            print("CRITICAL: State machine error, aborting")                                                # I don't how you did that, it shouldn't be possible. We could probably reset it
            operation.flight_state = ABORT                                                                  # but if it's a bug in the code, we should probably abort so it doesn't circle forever.
            operation.next_mission_state = LANDING                                                          # land and repeat.
        
        # Append next mission
        operation.mission.append()                                                                  # finally, append next mission state to mission list.