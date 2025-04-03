'''
UAS State Machine

Ted Tasman
2025-03-25
PSU UAS

This script implements a state machine for an Unmanned Aerial System (UAS) operation.

From MAVLink directory: ./ardupilot/Tools/autotest/sim_vehicle.py -v ArduPlane --console --map --custom-location 40.836055,-77.693492,0,343
'''

import uas_state_actions
from logging_config import configure_logging

# Configure logging
logger = configure_logging()


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

# STATUS STATES
OK = uas_state_actions.OK
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


def translate_mission_state(state):
    """
    Translate the mission state to a human-readable string.
    """
    state_translation = {
        PREFLIGHT: "PREFLIGHT",
        TAKEOFF_WAIT: "TAKEOFF WAIT",
        TAKEOFF: "TAKEOFF",
        DETECT: "DETECT",
        AIRDROP: "AIRDROP",
        LANDING: "LANDING",
        COMPLETE: "MISSION COMPLETE",
    }
    return state_translation.get(state, "Unknown State")


def main():

    # Initialize operation
    operation = uas_state_actions.Operation()

    # Load mission plan
    operation.load_plan('./testing/mission_plan_sample.txt')

    # Define actions
    actions = {
        PREFLIGHT: operation.preflight_check,
        TAKEOFF_WAIT: operation.takeoff_wait,
        TAKEOFF: operation.takeoff,
        DETECT: operation.detect,
        AIRDROP: operation.airdrop,
        LANDING: operation.land
    }

    while operation.next_mission_state != COMPLETE:

        logger.info(f"Current mission state: {translate_mission_state(operation.next_mission_state)}")

        # get action corresponding to the next mission state
        action = actions.get(operation.next_mission_state) 

        # Verify that the mission state is valid
        if action:
            
            # Check for abort
            if operation.status == ABORT:

                logger.critical("Operation aborted.")
                # just end the mission if we are idle or landing
                if operation.flight_state == IDLE or operation.next_mission_state == LANDING:
                    operation.next_mission_state = COMPLETE
                
                else: # in the air
                    operation.next_mission_state = LANDING # otherwise we need to land
            
            # Execute the action
            else:
                action()
                operation.append_next_mission()
                

        else:
            operation.next_mission_state = LANDING  # Fallback to landing state
            operation.status = ABORT
    
    logger.info("Operation ended.")


if __name__ == "__main__":
    main()
