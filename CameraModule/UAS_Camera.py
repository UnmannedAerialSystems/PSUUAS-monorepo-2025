'''
UAS_Camera
Author: Ted Tasman
Date: 2025-03-26

This module provides the functionality to capture images from a camera mounted on a UAS.
'''

import time
from picamera2 import Picamera2

class Camera:
    
    def __init__(self):

        self.picam2 = Picamera2()
        self.configure_camera(self.picam2)
    

    def configure_camera(self, picam2):
        '''
        picam2: Picamera2 - the Picamera2 object to configure

        Configures the camera for max resolution
        '''

        camera_config = picam2.create_still_configuration(main={"size": picam2.sensor_resolution})
        picam2.configure(camera_config)
    

    def capture_images(self, num_images, delay, directory):
        '''
        num_images: int - the number of images to capture
        delay: float - the delay in seconds between captures
        directory: str - the directory in which to save the images

        Captures num_images images with a delay of delay seconds between captures.
        Saves the images to the directory.
        '''

        self.picam2.start()
        print("Camera started. Capturing images...")

        image_count = 0
        while image_count < num_images:

            # create sequential filenames
            filename = f"{directory}/image_{image_count:04d}.jpg"

            # capture the image
            self.picam2.capture_file(filename)

            print(f"Captured: {filename}")
            image_count += 1

            # wait for the delay
            time.sleep(delay)
        
        print("\nStopping image capture...")
        self.picam2.stop()
        print("Camera stopped.")
        
