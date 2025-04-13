
# types: ignore[import]
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import random as rd
import os
import numpy as np
import cv2

class Runway:

    def __init__(self, runway_file, height=1080, y_offset=0, ratio=8, num_targets=4):
        '''
        runway_file: str - the path to the runway image
        height: int - the height of the runway on the image
        y_offset: int - the y offset of the runway on the image (top of the image to the top of the runway)
        ratio: int - the ratio of the width to the height of the runway
        num_targets: int - the number of targets to place on the runway
        '''

        self.height = height
        self.width = height * ratio
        self.y_offset = y_offset
        self.num_targets = num_targets
        self.runway = mpimg.imread(runway_file)
        self.points = self.select_coordinates()
        self.targets = self.select_targets(num_targets)

    def select_targets(self, num_targets):

        target_files = os.listdir(TARGETS_DIRECTORY)
        selected_files = rd.sample(target_files, num_targets)
        return selected_files
    

    def select_coordinates(self):

        points = []
        num_points = self.num_targets

        # generate num_points random points
        while num_points > 0:

            # generate a random point
            x = rd.randint(0, self.width - 1)
            y = rd.randint(self.y_offset, self.y_offset + self.height - 1)
            point = (x, y)

            # check if the point is at least 500px from any other point
            if all(np.linalg.norm(np.array(point) - np.array(p)) >= 500 for p in points):
                points.append(point)
                num_points -= 1

        return points
    

    def assign_targets(self):
        
        img_copy = self.runway.copy()
        runway_height, runway_width, _ = self.runway.shape

        # iterate over the selected files
        for i, target_file in enumerate(self.targets):

            # load the overlay image
            overlay_img = mpimg.imread(f'{TARGETS_DIRECTORY}/{target_file}')

            # Scale the overlay image to a maximum size of 200x200 while maintaining aspect ratio
            max_size = 200
            overlay_height, overlay_width, _ = overlay_img.shape
            scale_factor = min(max_size / overlay_width, max_size / overlay_height)
            new_width = int(overlay_width * scale_factor)
            new_height = int(overlay_height * scale_factor)
            overlay_img = cv2.resize(overlay_img, (new_width, new_height), interpolation=cv2.INTER_AREA)

            overlay_height, overlay_width, _ = overlay_img.shape

            # calculate the position to place the overlay image
            x_start = self.points[i][0] - overlay_width // 2
            y_start = self.points[i][1] - overlay_height // 2

            # Ensure the overlay image is within the bounds of the original image
            x_start = max(0, min(x_start, runway_width - overlay_width))
            y_start = max(0, min(y_start, runway_height - overlay_height))

            # Overlay the image
            for j in range(overlay_height):
                for k in range(overlay_width):
                    if overlay_img[j, k, 3] > 0.1:
                        img_copy[y_start + j, x_start + k, :3] = overlay_img[j, k, :3]
        
        self.runway = img_copy

            
    
    def generate_photos(self, num_photos, width=1920, height=1080, y=250):

        photos = []
        runway_height, runway_width, _ = self.runway.shape
        x = 0
        x_step = (runway_width - width) // (num_photos - 1) if num_photos > 1 else runway_width - width

        while x + width <= runway_width:

            # take photo at the current position
            img_copy = self.runway[y:y + height, x:x + width]

            # append the photo to the list with the coordinates
            photos.append((img_copy, (x, y)))

            # update the position
            x += x_step

            num_photos -= 1
        
        return photos


    def apply_motion_blur(self):
        # Apply motion blur to the runway image
        kernel_size = 15
        kernel = np.zeros((kernel_size, kernel_size))
        kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
        kernel /= kernel_size

        # Apply the kernel to the image
        blurred_img = cv2.filter2D(self.runway, -1, kernel)
        self.runway = blurred_img


TARGETS_DIRECTORY = './targets_2'

def main():
    runway = Runway("runway_smaller.png", height=800, y_offset=400, ratio=8, num_targets=4)
    runway.assign_targets()
    runway.apply_motion_blur()
    photos = runway.generate_photos(5)

    for i, photo in enumerate(photos):
        plt.imshow(photo[0])
        plt.title(f"Photo {i + 1}, Center: {photo[1]}")
        plt.show()


if __name__ == '__main__':
    main()