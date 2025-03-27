from pymavlink import mavutil
# Connect to the SITL instance
connection_string = 'tcp:127.0.0.1:5762'  # Adjust if using a different IP/port
master = mavutil.mavlink_connection(connection_string)

# Wait for a heartbeat from the SITL
print("Waiting for heartbeat...")
master.wait_heartbeat()
print(f"Heartbeat received from system (ID: {master.target_system})")


# send a waypoint
print("Sending waypoint")
master.mav.mission_item_int_send(
    0,
    0,
    0, # sequence id
    mavutil.mavlink.MAV_FRAME_GLOBAL, # frame
    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, # command for adding waypoint
    1, # current
    0, # autocontinue
    0, # p1
    0, # p2
    0, # p3
    0, # p4
    int(-35.36202696 *1e7), # latitude
    int(149.16196042 *1e7), # longitude
    600, # altitude
    mavutil.mavlink.MAV_MISSION_TYPE_MISSION # mission type
)

response = master.recv_match(type='MISSION_ACK', blocking=True)
print(response)