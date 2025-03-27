import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import random as rd
from PIL import Image
import numpy as np
import cv2

# Load an image from file
img = mpimg.imread('Image.png')

# Convert the image to a format suitable for OpenCV
img = (img * 255).astype('uint8')

# Preprocess the image
img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

# Run the ORB detector
orb = cv2.ORB_create()
keypoints, descriptors = orb.detectAndCompute(img, None)

# Get keypoint locations
keypoint_locations = np.array([kp.pt for kp in keypoints])  # (x, y) coordinates

# Draw keypoints on the image for visualization
output_image = cv2.drawKeypoints(img, keypoints, None, color=(0, 255, 0))

# Display the image
plt.imshow(output_image, cmap='gray')
plt.axis('off')
plt.show()