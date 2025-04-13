import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans # type: ignore

class ClusterORB:

    def __init__(
        self,
        n_clusters=10,
        n_features=512,
        scale_factor=1.2,
        n_levels=8,
        edge_threshold=31,
        first_level=5,
        wta_k=3,
        score_type=cv2.ORB_HARRIS_SCORE,
        patch_size=31,
        fast_threshold=20):
        """
        Initialize an ORB feature detector with the specified parameters.
        """
        self.orb = cv2.ORB_create(
            nfeatures=n_features,
            scaleFactor=scale_factor,
            nlevels=n_levels,
            edgeThreshold=edge_threshold,
            firstLevel=first_level,
            WTA_K=wta_k,
            scoreType=score_type,
            patchSize=patch_size,
            fastThreshold=fast_threshold)
        
        self.n_clusters = n_clusters
        self.all_points = np.empty((0, 0)) 
        self.img = None
        self.img_coords = None
        self.keypoints = None
        self.descriptors = None

    def prepare_img(self):
        
        img = (self.img * 255).astype('uint8')

        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        self.img = img
    

    def run_orb(self):
        """
        Run the ORB feature detector on the image and return keypoints and descriptors.
        """
        if self.orb is None:
            raise ValueError("ORB detector is not initialized. Please call initialize_orb() first.")

        self.keypoints, self.descriptors = self.orb.detectAndCompute(self.img, None)
    

    def prepare_keypoints(self):

        # Iterate over the keypoints
        for i, kp in enumerate(self.keypoints):
            
            # Get the keypoint coordinates
            kp_coords = kp.pt

            # Append the true coordinates to the list
            true_coords = (kp_coords[0] + self.img_coords[0], kp_coords[1] + self.img_coords[1])

            current_row = np.hstack([self.descriptors[i].tolist(), kp.size, kp.response, true_coords])

            # Initialize keypoints_true_coords if it's empty
            if self.all_points.size == 0:
                self.all_points = current_row
            else:
                self.all_points = np.vstack((self.all_points, current_row))
    

    def cluster(self):

        # initialize k-means clustering
        kmeans = MiniBatchKMeans(n_clusters=self.n_clusters, random_state=0)

        # Fit the k-means model
        kmeans.fit(self.all_points[:, -2:])

        # Analyze clusters
        clusters = kmeans.predict(self.all_points[:, -2:])
        cluster_info = {i: [] for i in range(kmeans.n_clusters)}
        for idx, cluster in enumerate(clusters):
            cluster_info[cluster].append(self.all_points[idx])
        
        return cluster_info, kmeans.cluster_centers_
    

    def process_image(self):
        """
        Process the image and prepare it for clustering.
        """
        # Prepare the image
        self.prepare_img()

        # Run ORB on the image
        self.run_orb()

        # Prepare keypoints and descriptors for clustering
        self.prepare_keypoints()

    
    def process_images(self, images):
        """
        Process a list of images and then cluster the keypoints.
        """
        for image in images:
            self.img = image[0]
            self.img_coords = image[1]
            self.process_image()
        
        return self.cluster()


def main():

    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from detect_zone_generator import Runway

    runway = Runway('../runway_smaller.png', height=800, y_offset=400, ratio=8, num_targets=4)
    runway.assign_targets()
    photos = runway.generate_photos(5)

    orb = ClusterORB(n_clusters=50, n_features=512)

    runway_img = runway.runway.copy()

    import matplotlib.pyplot as plt

    # Process the images and get cluster information
    cluster_info, cluster_centers = orb.process_images(photos)

    # Plot the runway image
    plt.imshow(cv2.cvtColor(runway_img, cv2.COLOR_BGR2RGB))
    plt.title("Clustered Keypoints on Runway")

    # Plot true target coordinates
    for i, target in enumerate(runway.points):
        plt.scatter(target[0], target[1], c='black', marker='x', label=f"Target {i+1}")

    # Plot cluster centers
    cluster_centers = np.array(cluster_centers)
    plt.scatter(cluster_centers[:, 0], cluster_centers[:, 1], c='red', marker='+', s=100, label="Cluster Centers")

    plt.show()

if __name__ == "__main__":
    main()






        