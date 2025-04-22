import torch
import torch.nn as nn
import torchvision.transforms as transforms # type: ignore
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import cv2
import random
from tqdm import tqdm # type: ignore

from ls2_network import LS2Network
from detect_zone_generator import Runway

# ---- CONFIG ---- #
MODEL_PATH = "lion_sight_2_model.pth"
TARGETS_DIRECTORY = "./targets_2"
RUNWAY_IMAGE = "runway_smaller.png"
CROP_SIZE = 224
NUM_EPOCHS = 1000

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if DEVICE.type == "cuda":
    print(f"Using GPU: {torch.cuda.get_device_name(0)}")
else:
    print("Using CPU")

# ---------------- #

# === Define same transform as in training === #
transform = transforms.Compose([
    transforms.Resize((CROP_SIZE, CROP_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# === Load your trained model === #
from torchvision import models

model = models.mobilenet_v2(pretrained=False)
model.classifier = nn.Sequential(
    nn.Linear(model.last_channel, 512),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(512, 1),
)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE))
model.to(DEVICE)
model.eval()

# === Generate test scene === #
def generate_test_scene():
    runway = Runway(RUNWAY_IMAGE, height=800, y_offset=400, ratio=8, num_targets=8)
    runway.assign_targets()
    runway.apply_motion_blur()
    return runway

# Sample background points (guaranteed to be > 400px from true objects)
def sample_background_points(num_points, image_shape, exclude_points, min_dist=400):
    h, w = image_shape[:2]
    bg_points = []
    attempts = 0
    while len(bg_points) < num_points and attempts < 1000:
        x = random.randint(112, w - 112)
        y = random.randint(112, h - 112)
        if all(np.linalg.norm(np.array((x, y)) - np.array(tp)) >= min_dist for tp in exclude_points):
            bg_points.append((x, y))
        attempts += 1
    return bg_points

# === Evaluate and display results === #
def crop_and_predict(img, point):
    x, y = point
    x_start = max(0, x - CROP_SIZE // 2)
    y_start = max(0, y - CROP_SIZE // 2)
    x_end = x_start + CROP_SIZE
    y_end = y_start + CROP_SIZE
    crop = img[y_start:y_end, x_start:x_end]

    crop_uint8 = (crop * 255).astype(np.uint8) if crop.dtype != np.uint8 else crop
    crop_pil = Image.fromarray(cv2.cvtColor(crop_uint8, cv2.COLOR_BGR2RGB))

    input_tensor = transform(crop_pil).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        output = model(input_tensor)
        prob = torch.sigmoid(output).item()
    return crop_uint8, prob, output.item()

print("=== Testing Generalization on Object and Background Patches ===\n")

progress_bar = tqdm(total=NUM_EPOCHS, desc="Testing", unit="epoch")
no_count = 0
yes_count = 0
for epoch in range(NUM_EPOCHS):

    runway = generate_test_scene()
    true_targets = runway.points.copy()
    bg_points = sample_background_points(10, runway.runway.shape, true_targets)

    # Test true targets
    for i, pt in enumerate(true_targets):
        crop, prob, logit = crop_and_predict(runway.runway, pt)
        if prob:
            output_path = f"./train_p2/object_present/true_target_{no_count}.png"
            #cv2.imwrite(output_path, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            plt.imshow(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            plt.title(f"Prob: {prob}, Logit: {logit}")
            plt.axis('off')
            plt.show()
            no_count += 1

    # Test background points
    for i, pt in enumerate(bg_points):
        crop, prob,logit = crop_and_predict(runway.runway, pt)
        if prob >= 0.5:
            output_path = f"./train_p2/no_object/background_point_{yes_count}.png"
            #cv2.imwrite(output_path, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
            plt.imshow(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            plt.title(f"Prob: {prob}, Logit: {logit}")
            plt.axis('off')
            plt.show()
            yes_count += 1

    progress_bar.update(1)
