'''
PSU UAS Camera Emulator
Author: Ted Tasman
Date: 2025-03-26

This module emulates the functionality of UAS_Camera.py. It is used to test the camera module without the need of a drone.
'''

import time
import matplotlib.image as mpimg
import os
import random as rd
import numpy as np


class Camera:

    def __init__(self, backdrop_file, resolution, area_y_offset=0, area_width=0, area_height=0, num_targets=0, targets_folder=None, y_offset=0):
        '''
        backdrop_file: str - the path to the backdrop image
        targets_folder: str - the path to the folder containing the target images
        num_targets: int - the number of targets to place on the backdrop
        resolution: tuple - the resolution of the camera
        area_width: int - the width in pixels of the area in which the targets will be placed
        area_height: int - the height in pixels of the area in which the targets will be placed
        area_y_offset: int - the y offset of the area in which the targets will be placed (top of the image to the top of the area)
        '''

        self.resolution = resolution
        self.backdrop = mpimg.imread(backdrop_file)
        self.y_offset = y_offset
        self.area_y_offset = area_y_offset
        self.area_width = area_width
        self.area_height = area_height
        self.num_targets = num_targets
        self.targets_folder = targets_folder
        self.area = None


    def select_targets(self, num_targets, targets_folder):
        '''
        num_targets: int - the number of targets to select
        targets_folder: str - the path to the folder containing the target images

        Returns a list of num_targets target files
        '''

        target_files = os.listdir(targets_folder)
        selected_files = rd.sample(target_files, num_targets)
        return selected_files
    

    def select_coordinates(self, num_points, width, height, y_offset):
        '''
        num_points: int - the number of points to select
        width: int - the width in pixels of the area in which the points will be placed
        height: int - the height in pixels of the area in which the points will be placed
        y_offset: int - the y offset of the area in which the points will be placed (top of the image to the top of the area)

        Returns a list of num_points points
        '''

        points = []

        # generate num_points random points
        while num_points > 0:

            # generate a random point
            x = rd.randint(0, width - 1)
            y = rd.randint(y_offset, y_offset + height - 1)
            point = (x, y)

            # check if the point is at least 500px from any other point
            if all(np.linalg.norm(np.array(point) - np.array(p)) >= 500 for p in points):
                points.append(point)
                num_points -= 1

        return points
    

    def assign_targets(self, num_targets, targets_folder, area_width, area_height, area_y_offset):
        '''
        num_targets: int - the number of targets to place on the backdrop
        targets_folder: str - the path to the folder containing the target images
        area_width: int - the width in pixels of the area in which the targets will be placed
        area_height: int - the height in pixels of the area in which the targets will be placed
        area_y_offset: int - the y offset of the area in which the targets will be placed (top of the image to the top of the area)

        Calls select_targets and select_coordinates to assign targets to the backdrop
        '''

        targets = self.select_targets(num_targets, targets_folder)
        points = self.select_coordinates(num_targets, area_width, area_height, area_y_offset)
        backdrop_copy = self.backdrop.copy()

        for target, point in zip(targets, points):
            
            # load the overlay image
            overlay_img = mpimg.imread(f'{targets_folder}/{target}')
            overlay_height, overlay_width, _ = overlay_img.shape

            # calculate the position to place the overlay image
            x_start = point[0] - overlay_width // 2
            y_start = point[1] - overlay_height // 2

            # Ensure the overlay image is within the bounds of the original image
            x_start = max(0, min(x_start, area_width - overlay_width))
            y_start = max(0, min(y_start, area_height - overlay_height))

            # Overlay the image
            for j in range(overlay_height):
                for k in range(overlay_width):
                    if overlay_img[j, k, 3] > 0.1:
                        backdrop_copy[y_start + j, x_start + k, :3] = overlay_img[j, k, :3]
            
        return backdrop_copy
    

    def generate_photos(self, num_photos, y_offset, delay=0.5, directory=None):
        '''
        num_photos: int - the number of photos to generate
        y_offset: int - the y offset of the area in which the photos will be taken (top of the image to the top of the area)
        delay: float - the delay between captures

        Generates photos of the area with the targets
        '''

        photos = []
        backdrop_height, backdrop_width, _ = self.area.shape
        width, height = self.resolution

        x = 0
        x_step = (backdrop_width - width) // (num_photos - 1) if num_photos > 1 else backdrop_width - width

        i = 0

        while x + width <= backdrop_width and i < num_photos:
            
            # take photo at the current position
            img_copy = self.area[y_offset:y_offset + height, x:x + width]

            # append the photo to the list with the coordinates
            photos.append((img_copy, (x, y_offset)))

            # update the position
            x += x_step

            i += 1

            filename = os.path.join(directory, f"image_{i:03d}.jpg")  # Save images with sequential names in the specified directory
            mpimg.imsave(filename, img_copy)
            print(f"Captured: {filename}")

            # sleep for the delay
            time.sleep(delay)
        
        return photos


    def capture_images(self, num_photos, delay=0.5, directory=None):
        '''
        num_photos: int - the number of photos to capture
        delay: float - the delay between captures

        Drives the class and matches the functionality of UAS_Camera.py
        '''

        # assign targets to the backdrop
        self.area = self.assign_targets(self.num_targets, self.targets_folder, self.area_width, self.area_height, self.area_y_offset)
        
        # generate photos
        self.generate_photos(num_photos, self.y_offset, delay, directory)

        return 1
    
        
    
def main():

    Cam = Camera(
                    backdrop_file='runway_smaller.png',
                    resolution=(1440, 1080),
                    area_y_offset=400,
                    area_height=800,
                    area_width=6400,
                    num_targets=4,
                    targets_folder='./targets_small',
                    y_offset=250
                 )
    
    # Create a new directory with a unique name
    directory = f"photos_{time.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(directory, exist_ok=True)

    success = Cam.capture_images(5, 0.5, directory)

    if success:
        print("\nStopping image capture...")
    else:
        print("\nImage capture failed.")


if __name__ == "__main__":
    main()