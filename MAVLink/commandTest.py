from pymavlink import mavutil
import time

'''START COMMAND
./MAVLink/ardupilot/Tools/autotest/sim_vehicle.py -v ArduPlane --console --map --custom-location 38.31527628,-76.54908330,40,282.5
'''
# Connect to the SITL instance
connection_string = 'tcp:127.0.0.1:5762'  # Adjust if using a different IP/port
master = mavutil.mavlink_connection(connection_string)

# Wait for a heartbeat from the SITL
print("Waiting for heartbeat...")
master.wait_heartbeat()
print(f"Heartbeat received from system (ID: {master.target_system})")


# Find the mode ID for GUIDED mode
mode = 'AUTO'

if mode not in master.mode_mapping():
    print('Unknown mode : {}'.format(mode))
    print('Try:', list(master.mode_mapping().keys()))

mode_id = master.mode_mapping()[mode]

# Run prearm checks
print("Performing prearm checks")
message = master.mav.command_long_encode(
    0,
    0,
    mavutil.mavlink.MAV_CMD_RUN_PREARM_CHECKS,
    0, 
    1,
    0,
    0,
    0,
    0,
    0,
    0
)

master.mav.send(message)
response = master.recv_match(type='COMMAND_ACK', blocking=True)
print(response)

# Arm the vehicle
print("Arming the vehicle")
message = master.mav.command_long_encode(
    0,
    0,
    mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
    0, 
    1,
    0,
    0,
    0,
    0,
    0,
    0
)

master.mav.send(message)
response = master.recv_match(type='COMMAND_ACK', blocking=True)
print(response)

# takeoff
print("Taking off")
message = master.mav.command_long_encode(
    0,
    0,
    mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    0, # confirmation
    0, # param1
    0, # param2
    0, # param3
    0, # param4
    0, # param5
    0, # param6
    20  # param7
)

master.mav.send(message)

response = master.recv_match(type='COMMAND_ACK', blocking=True)
print(response)

# Set the vehicle mode
print("Setting mode to AUTO")
message = master.mav.command_long_encode(
    0,
    0,
    mavutil.mavlink.MAV_CMD_DO_SET_MODE,
    0,
    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
    mode_id,
    0,
    0,
    0,
    0,
    0
)

master.mav.send(message)

response = master.recv_match(type='COMMAND_ACK', blocking=True)
print(response)




'''
self.upload_simple_relhome_mission([
    (mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 20),
    (mavutil.mavlink.MAV_CMD_NAV_WAYPOINT, 20, 0, 20),
    (mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0, 0, 0),
])

def upload_simple_relhome_mission(self, items, target_system=1, target_component=1):
    mission = self.create_simple_relhome_mission(
        items,
        target_system=target_system,
        target_component=target_component)
    self.check_mission_upload_download(mission)

def check_mission_upload_download(self, items, strict=True):
        self.check_mission_item_upload_download(
            items,
            "waypoints",
            mavutil.mavlink.MAV_MISSION_TYPE_MISSION,
            strict=strict)
        if self.use_map and self.mavproxy is not None:
            self.mavproxy.send('wp list\n')


def upload_using_mission_protocol(self, mission_type, items):
    mavlink2 required
    target_system = 1
    target_component = 1
    self.do_timesync_roundtrip()
    tstart = self.get_sim_time()
    self.mav.mav.mission_count_send(target_system,
                                    target_component,
                                    len(items),
                                    mission_type)
    remaining_to_send = set(range(0, len(items)))
    sent = set()
    timeout = (10 + len(items)/10.0)
    while True:
        if self.get_sim_time_cached() - tstart > timeout:
            raise NotAchievedException("timeout uploading %s" % str(mission_type))
        if len(remaining_to_send) == 0:
            self.progress("All sent")
            break
        m = self.mav.recv_match(type=['MISSION_REQUEST', 'MISSION_ACK'],
                                blocking=True,
                                timeout=1)
        if m is None:
            continue

        if m.get_type() == 'MISSION_ACK':
            if (m.target_system == 255 and
                    m.target_component == 0 and
                    m.type == 1 and
                    m.mission_type == 0):
                # this is just MAVProxy trying to screw us up
                continue
            raise NotAchievedException(f"Received unexpected mission ack {self.dump_message_verbose(m)}")

        self.progress("Handling request for item %u/%u" % (m.seq, len(items)-1))
        self.progress("Item (%s)" % str(items[m.seq]))
        if m.seq in sent:
            self.progress("received duplicate request for item %u" % m.seq)
            continue

        if m.seq not in remaining_to_send:
            raise NotAchievedException("received request for unknown item %u" % m.seq)

        if m.mission_type != mission_type:
            raise NotAchievedException("received request for item from wrong mission type")

        if items[m.seq].mission_type != mission_type:
            raise NotAchievedException(f"supplied item not of correct mission type (want={mission_type} got={items[m.seq].mission_type}")  # noqa:501
        if items[m.seq].target_system != target_system:
            raise NotAchievedException("supplied item not of correct target system")
        if items[m.seq].target_component != target_component:
            raise NotAchievedException("supplied item not of correct target component")
        if items[m.seq].seq != m.seq:
            raise NotAchievedException("supplied item has incorrect sequence number (%u vs %u)" %
                                        (items[m.seq].seq, m.seq))

        items[m.seq].pack(self.mav.mav)
        self.mav.mav.send(items[m.seq])
        remaining_to_send.discard(m.seq)
        sent.add(m.seq)

        timeout += 10  # we received a good request for item; be generous with our timeouts

    m = self.assert_receive_message('MISSION_ACK', timeout=1)
    if m.mission_type != mission_type:
        raise NotAchievedException("Mission ack not of expected mission type")
    if m.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
        raise NotAchievedException("Mission upload failed (%s)" %
                                    (mavutil.mavlink.enums["MAV_MISSION_RESULT"][m.type].name),)
    self.progress("Upload of all %u items succeeded" % len(items))'''