import torch
import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans # type: ignore
from ls2_cluster_orb import ClusterORB
from ls2_network import LS2Network
import os

class LionSight2:

    def __init__(self, num_targets, net, orb):
        self.num_targets = num_targets
        self.orb = orb
        self.net = net
        self.images = None
    

    def load_images(self, images_directory):
        '''
        Load images from the specified path.
        '''
        image_names = [filename for filename in os.listdir(images_directory) if filename.endswith(".png")]
        images = []
        for filename in image_names:
            image = cv2.imread(os.path.join(images_directory, filename))
            if image is not None:
                image_coords = filename.split('_')[1]
                image_coords = tuple(image_coords.strip('()').split(','))
                image_coords = (int(image_coords[0]), int(image_coords[1]))
                image = (image, image_coords)
                images.append(image)
            else:
                print(f"Error loading image: {filename}")
        self.images = images

    
    def detect(self):
        '''
        Detect objects in the images using the neural network and ORB feature detector.
        '''

        # Process 
        cluster_info, cluster_centers = self.orb.process_images(self.images)

        # Initialize a list to store the results
        results = []

        # Determine which photos contain which clusters
        for center in cluster_centers:
            # Get the coordinates of the cluster center
            x, y = int(center[0]), int(center[1])

            # track the number of images containing the center and positive detections
            num_images = 0
            prediction_sum = 0

            # Check which photo contains the cluster center
            for i, image in enumerate(self.images):

                left = image[1][0]
                right = image[1][0] + image[0].shape[1]
                top = image[1][1]
                bottom = image[1][1] + image[0].shape[0]

                

                if left <= x <= right and top <= y <= bottom:
                    print(f"{left}\t<= {x}\t<=\t{right} and {top}\t<=\t{y} <=\t{bottom}")
                    num_images += 1

                    image_x = x - left
                    image_y = y - top

                    self.net.crop_to_poi(image[0], (image_x, image_y), 224)
                    output = self.net.run_net()

                    prediction_sum += output
                
            # Calculate the average prediction
            if num_images > 0:
                avg_prediction = prediction_sum / num_images
            else:
                avg_prediction = 0

            # Append the result to the list
            results.append((x, y, avg_prediction))

        return results, cluster_centers


def main():

    import sys
    import os
    from detect_zone_generator import Runway
    import matplotlib.pyplot as plt

    runway = Runway('./runway_smaller.png', height=800, y_offset=400, ratio=3, num_targets=4)
    runway.assign_targets()
    runway.apply_motion_blur()
    photos = runway.generate_photos(20)

    # Create a directory to save photos if it doesn't exist
    output_dir = "test_photos"
    os.makedirs(output_dir, exist_ok=True)
    # Save the generated photos to the directory
    for i, photo in enumerate(photos):
        photo_to_save = (photo[0] * 255).astype(np.uint8) if photo[0].dtype != np.uint8 else photo[0]
        photo_path = os.path.join(output_dir, f"photo_{photo[1][0]},{photo[1][1]}_.png")
        cv2.imwrite(photo_path, photo_to_save)

    orb = ClusterORB(n_clusters=20, n_features=1024)
    net = LS2Network("lion_sight_2_model.pth")
    lion_sight = LionSight2(num_targets=4, net=net, orb=orb)

    lion_sight.load_images(output_dir)
    results, centers = lion_sight.detect()


    # Plot the cluster centers
    for center in centers:
        plt.scatter(center[0], center[1], c='blue', marker='o', s=50, label="Cluster Center")

    # get the best 4 predictions
    best_points = sorted(results, key=lambda x: x[2], reverse=True)[:4]
    
    runway_img = runway.runway.copy()

    # Plot the runway image
    plt.imshow(cv2.cvtColor(runway_img, cv2.COLOR_BGR2RGB))
    plt.title("Clustered Keypoints on Runway")

    # Plot true target coordinates
    for i, target in enumerate(runway.points):
        plt.scatter(target[0], target[1], c='black', marker='x', label=f"Target {i+1}")

    # Plot best cluster centers
    best_points = np.array(best_points)
    plt.scatter(best_points[:, 0], best_points[:, 1], c='red', marker='+', s=100, label="Best Points")

    plt.show()


    

if __name__ == "__main__":
    main()






        