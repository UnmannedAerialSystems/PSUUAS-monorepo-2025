import os
import random as rd
import numpy as np
import cv2
from tqdm import tqdm # type: ignore
import matplotlib.pyplot as plt

def prepare_directories():
    '''
    Prepare the directories for the training data generation.
    '''

    # Create the output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)
    
    if not os.path.exists(os.path.join(OUTPUT_DIRECTORY, TRUE_DIRECTORY)):
        os.makedirs(os.path.join(OUTPUT_DIRECTORY, TRUE_DIRECTORY))
    
    if not os.path.exists(os.path.join(OUTPUT_DIRECTORY, FALSE_DIRECTORY)):
        os.makedirs(os.path.join(OUTPUT_DIRECTORY, FALSE_DIRECTORY))



def rotate_image(image, angle, border_mode=cv2.BORDER_CONSTANT):
    """
    Rotate the image by the specified angle.
    """
    # Get the image dimensions
    height, width = image.shape[:2]

    # Calculate the new dimensions of the canvas
    diagonal = int(np.sqrt(height**2 + width**2))  # Diagonal of the image
    new_width = diagonal
    new_height = diagonal

    # Get the rotation matrix
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Adjust the rotation matrix to account for the new canvas size
    rotation_matrix[0, 2] += (new_width - width) // 2
    rotation_matrix[1, 2] += (new_height - height) // 2

    # Perform the rotation with the expanded canvas
    rotated_image = cv2.warpAffine(image, rotation_matrix, (new_width, new_height), borderMode=border_mode, borderValue=(0, 0, 0, 0))

    return rotated_image


def sample_target(target_images):
    """
    Load the target image from the specified file.
    """
    overlay_img = rd.choice(target_images)

    # Randomly rotate the target image
    angle = rd.uniform(0, 360)  # Random angle between 0 and 360 degrees
    rotated_overlay = rotate_image(overlay_img, angle)

    # Resize the image to the desired size
    target_height, target_width, _ = rotated_overlay.shape
    
    # Calculate random scaling factor
    scale_factor = rd.uniform(OVERLAY_SCALE_MIN, OVERLAY_SCALE_MAX)

    # Calculate new dimensions for the target image while maintaining aspect ratio
    aspect_ratio = target_width / target_height
    if aspect_ratio > 1:  # Wider than tall
        new_width = int(INPUT_SIZE[0] * scale_factor)
        new_height = int(new_width / aspect_ratio)
    else:  # Taller than wide or square
        new_height = int(INPUT_SIZE[1] * scale_factor)
        new_width = int(new_height * aspect_ratio)

    # Resize the target image
    rotated_overlay = cv2.resize(rotated_overlay, (new_width, new_height))

    return rotated_overlay


def sample_background(background_images, width, height):
    """
    Load the background image from the specified file.
    """
    background_img = rd.choice(background_images)

    # Randomly rotate the background image
    angle = rd.uniform(0, 360)  # Random angle between 0 and 360 degrees
    rotated_background = rotate_image(background_img, angle, border_mode=cv2.BORDER_REFLECT)

    # Pick a random start position for cropping
    rotated_height, rotated_width, _ = rotated_background.shape
    x_start = rd.randint(0, rotated_width - width)
    y_start = rd.randint(0, rotated_height - height)

    # Crop the image to the desired size
    cropped_background = rotated_background[y_start:y_start + height, x_start:x_start + width]

    return cropped_background


def export_sample(image, index, label):
    """
    Save the generated image to the specified output path.
    """

    label_directory = TRUE_DIRECTORY if label == 1 else FALSE_DIRECTORY

    # save the image to the output directory
    output_path = os.path.join(OUTPUT_DIRECTORY, label_directory, f'image_{index}.jpg')

    # Normalize the image if it is a floating-point array
    if image.dtype == np.float32 or image.dtype == np.float64:
        image = np.clip(image, 0, 1)
    plt.imsave(output_path, image)


def apply_motion_blur(image, kernel_size, angle):
    '''
    Apply motion blur to the image.
    '''
    # Create the motion blur kernel
    kernel = np.zeros((kernel_size, kernel_size))
    kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)

    kernel = kernel / kernel_size

    # Rotate the kernel
    kernel = rotate_image(kernel, angle)
    kernel = kernel / np.sum(kernel)

    # Apply the kernel to the image
    blurred_image = cv2.filter2D(image, -1, kernel)
    return blurred_image


def generate_training_data(num_samples):
    '''
    Generate training data by overlaying target images on background images.
    '''

    # Load the target and background images
    target_files = [file for file in os.listdir(TARGETS_DIRECTORY) if file.lower().endswith(('.png', '.jpg', '.jpeg'))]
    background_files = [file for file in os.listdir(BACKGROUND_DIRECTORY) if file.lower().endswith(('.png', '.jpg', '.jpeg'))]

    # Load target images with alpha channel
    target_images = [
        cv2.cvtColor(cv2.imread(os.path.join(TARGETS_DIRECTORY, file), cv2.IMREAD_UNCHANGED), cv2.COLOR_BGRA2RGBA)
        for file in target_files
    ]

    # Load background images (no alpha channel needed)
    background_images = [
        cv2.cvtColor(cv2.imread(os.path.join(BACKGROUND_DIRECTORY, file)), cv2.COLOR_BGR2RGB)
        for file in background_files
    ]

    i = 0
    with tqdm(total=num_samples, desc="Generating Samples") as pbar:
        while i < num_samples:
            # Select a random target and background
            overlay_img = sample_target(target_images)
            background_img = sample_background(background_images, INPUT_SIZE[0], INPUT_SIZE[1])

            # Select a random motion blur kernel size and angle
            kernel_size = rd.randint(MOTION_BLUR_KERNEL_MIN, MOTION_BLUR_KERNEL_MAX)
            angle = rd.uniform(0, 360)

            # Apply motion blur to the background image
            empty_img = apply_motion_blur(background_img.copy(), kernel_size, angle)

            export_sample(empty_img, i, 0)
            i += 1
            pbar.update(1)

            # Get the dimensions of the overlay and background images
            overlay_height, overlay_width, _ = overlay_img.shape
            background_height, background_width, _ = background_img.shape

            # Allow the overlay to leave the frame up to 50%
            max_offset_x = int(overlay_width * 0.5)
            max_offset_y = int(overlay_height * 0.5)

            # Select a random position for the overlay image
            x_start = rd.randint(-max_offset_x, background_width - overlay_width + max_offset_x)
            y_start = rd.randint(-max_offset_y, background_height - overlay_height + max_offset_y)

            x_end = x_start + overlay_width
            y_end = y_start + overlay_height

            overlay_x_start = 0
            overlay_x_end = overlay_width
            overlay_y_start = 0
            overlay_y_end = overlay_height

            # if x_start < 0, we need to truncate the overlay image
            if x_start < 0:
                overlay_x_start = -x_start
                x_start = 0
            
            # if y_start < 0, we need to truncate the overlay image
            if y_start < 0:
                overlay_y_start = -y_start
                y_start = 0
            
            # if x_end > background_width, we need to truncate the overlay image
            if x_end > background_width:
                overlay_x_end = overlay_width - (x_end - background_width)
                x_end = background_width

            # if y_end > background_height, we need to truncate the overlay image
            if y_end > background_height:
                overlay_y_end = overlay_height - (y_end - background_height)
                y_end = background_height

            # Create a mask for the alpha channel
            alpha_mask = overlay_img[overlay_y_start:overlay_y_end, overlay_x_start:overlay_x_end, 3] > 0.1

            # Overlay the image using the mask
            background_img[y_start:y_end, x_start:x_end, :3][alpha_mask] = overlay_img[overlay_y_start:overlay_y_end, overlay_x_start:overlay_x_end, :3][alpha_mask]

            # Apply motion blur to the image
            background_img = apply_motion_blur(background_img, kernel_size, angle)

            # Save the image
            export_sample(background_img, i, 1)
            i += 1
            pbar.update(1)

    print(f'\nGenerated {num_samples} training samples.')


TARGETS_DIRECTORY = '../targets_2'
BACKGROUND_DIRECTORY = '../backgrounds_upscaled'
OUTPUT_DIRECTORY = './training_data'
TRUE_DIRECTORY = 'object_present'
FALSE_DIRECTORY = 'no_object'

# Parameters
INPUT_SIZE = (512, 512)
NUM_SAMPLES = 1000
MOTION_BLUR_KERNEL_MIN = 1
MOTION_BLUR_KERNEL_MAX = 30
OVERLAY_SCALE_MIN = 0.1
OVERLAY_SCALE_MAX = 0.5


def main():
    '''
    Main function to generate training data.
    '''
    # Prepare directories
    prepare_directories()
    # Generate training data
    generate_training_data(NUM_SAMPLES)

if __name__ == '__main__':
    main()






