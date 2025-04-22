from MAVez.mav_controller import Controller
from MAVez.Mission import Mission
from pymavlink import mavutil

controller = Controller(connection_string="/dev/ttyACM0")

mission = Mission(controller)

mission.load_mission_from_file("test.txt")

mission.send_mission()