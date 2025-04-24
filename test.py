from MAVez.mav_controller import Controller
from MAVez.Mission import Mission
from pymavlink import mavutil

controller = Controller(connection_string="/dev/tty.usbmodem1301")

controller.set_home()

mission = Mission(controller)

mission.load_mission_from_file("test.txt")

mission.send_mission()

controller.set_mode("AUTO")