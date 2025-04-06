from MavEZ.flight_manger import Flight
import time

flight = Flight(connection_string='/dev/tty.usbmodem11301')

flight.wait_for_channel_input(channel=6, value=982, timeout=10, wait_time=120, value_tolerance=100)


flight.controller.set_mode('FBWB')
print("Switching to AUTO mode")


#flight.controller.set_servo(10, 800)

#time.sleep(2)

#flight.controller.set_servo(10, 2100)

