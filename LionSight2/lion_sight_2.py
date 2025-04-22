import torch
import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans # type: ignore
from ls2_cluster_orb import ClusterORB
from ls2_network import LS2Network
import os
from PIL import Image
from tqdm import tqdm # type: ignore

class LionSight2:

    def __init__(self, num_targets, net, orb):
        self.num_targets = num_targets
        self.orb = orb
        self.net = net
        self.images = None
        self.true_points = None
    

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
    

    def detect_dense(self, stride=32, crop_size=224):
        """
        Densely scan the entire stitched area, score with the network, and return top-K detections.
        """
        # Determine full bounds of stitched image
        min_x = min(img[1][0] for img in self.images)
        min_y = min(img[1][1] for img in self.images)
        max_x = max(img[1][0] + img[0].shape[1] for img in self.images)
        max_y = max(img[1][1] + img[0].shape[0] for img in self.images)

        stitched_width = max_x - min_x
        stitched_height = max_y - min_y

        print(f"Stitched image size: {stitched_width} x {stitched_height}")

        results = []

        total_positions = ((max_y - min_y - crop_size) // stride) * ((max_x - min_x - crop_size) // stride)
        progress_bar = tqdm(total=total_positions, desc="Dense CNN Scan")

        for y in range(min_y, max_y - crop_size, stride):
            for x in range(min_x, max_x - crop_size, stride):

                # Find which image contains this patch
                for img, origin in self.images:
                    img_x, img_y = origin
                    img_h, img_w = img.shape[:2]

                    # Does this image cover the crop?
                    if (img_x <= x < img_x + img_w - crop_size and
                        img_y <= y < img_y + img_h - crop_size):

                        rel_x = x - img_x
                        rel_y = y - img_y

                        # Crop the patch
                        crop = img[rel_y:rel_y+crop_size, rel_x:rel_x+crop_size]
                        self.net.img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                        score = self.net.run_net()
                        
                        # if this should contain a true point
                        for true_point in self.true_points:
                            true_x, true_y = true_point
                            if (x <= true_x < x + crop_size and
                                y <= true_y < y + crop_size):
                                
                                # display the crop with score
                                cv2.imshow(f"{score}", crop)
                                cv2.waitKey(0)
                                cv2.destroyAllWindows()

                        if score > 50:
                            cv2.imshow(f"{score}", crop)
                            cv2.waitKey(1)
                            cv2.destroyAllWindows()

                        results.append((x, y, score))
                        break  # Only use one image per crop

                progress_bar.update(1)

        return results
    

    def get_nms(self, detections, distance_threshold=200, top_k=4):
        """
        Apply Non-Maximum Suppression (NMS) to filter out overlapping detections.
        """
        # Sort results by score
        detections = sorted(detections, key=lambda x: x[2], reverse=True)

        # Initialize a list to hold the final results
        final_results = []

        while detections:
            # Take the highest score detection
            best = detections.pop(0)
            final_results.append(best)

            detections = [
                d for d in detections
                if np.linalg.norm(np.array(d[:2]) - np.array(best[:2])) > distance_threshold
            ]

        return final_results[:top_k]



def main():

    import sys
    import os
    from detect_zone_generator import Runway
    import matplotlib.pyplot as plt

    runway = Runway('./runway_smaller.png', height=800, y_offset=400, ratio=8, num_targets=4)
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
    lion_sight.true_points = runway.points
    lion_sight.load_images(output_dir)
    results = lion_sight.detect_dense()
    best_100 = lion_sight.get_nms(results, distance_threshold=100, top_k=20)
    best_200 = lion_sight.get_nms(results, distance_threshold=200, top_k=20)
    best_300 = lion_sight.get_nms(results, distance_threshold=300, top_k=20)

    # # Plot the cluster centers
    # for center in centers:
    #     plt.scatter(center[0], center[1], c='blue', marker='o', s=50, label="Cluster Center")

    # # get the best 4 predictions
    # best_points = sorted(results, key=lambda x: x[2], reverse=True)[:4]
    
    runway_img = runway.runway.copy()

    # Plot the runway image
    plt.imshow(cv2.cvtColor(runway_img, cv2.COLOR_BGR2RGB))
    plt.title("Clustered Keypoints on Runway")

    # Plot true target coordinates
    for i, target in enumerate(runway.points):
        plt.scatter(target[0], target[1], c='black', marker='x', label=f"Target {i+1}")

    # Plot best cluster centers
    best_100 = np.array(best_100)
    best_200 = np.array(best_200)
    best_300 = np.array(best_300)
    plt.scatter(best_100[:, 0], best_100[:, 1], c='red', marker='+', s=100, label="Best 100")
    plt.scatter(best_200[:, 0], best_200[:, 1], c='green', marker='o', s=100, label="Best 200")
    plt.scatter(best_300[:, 0], best_300[:, 1], c='blue', marker='*', s=100, label="Best 300")
    
    plt.show()


    

if __name__ == "__main__":
    main()






        