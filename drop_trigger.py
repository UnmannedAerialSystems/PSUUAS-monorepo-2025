'''
Ted Tasman
PSU UAS
2025-04-08
Triggers the airdrop release
'''

import time

class AirdropTrigger:

    def __init__(self, flight, servo_index, open_pwm, close_pwm, prime_pwm):
        self.flight = flight
        self.servo_index = servo_index
        self.open_pwm = open_pwm
        self.close_pwm = close_pwm
        self.prime_pwm = prime_pwm
    
    def trigger(self):
        

        # prime the release
        self.flight.controller.set_servo(self.servo_index, self.prime_pwm)
        time.sleep(2)

        # release the drop
        self.flight.controller.set_servo(self.servo_index, self.open_pwm)

    def load(self):

        # jump to open position
        self.flight.controller.set_servo(self.servo_index, self.open_pwm)
        time.sleep(2)
        # prime the release
        self.flight.controller.set_servo(self.servo_index, self.prime_pwm)
        
        # wait for close signal
        input('Press enter to close the drop...')

        # close the drop
        self.flight.controller.set_servo(self.servo_index, self.close_pwm)


def main():
    from MAVez.flight_manger import Flight
    flight = Flight('/dev/tty.usbmodem21401')

    print(flight.controller.master.param_fetch_all())
    
    

if __name__ == '__main__':
    main()