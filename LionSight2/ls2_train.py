import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Subset
from sklearn.model_selection import train_test_split
from tqdm import tqdm # type: ignore
from torchvision import transforms, datasets, models # type: ignore
import os
from collections import Counter

# === CONFIG === #
TRAIN_DIRECTORY = './train_p2'
NUM_EPOCHS = 80
BATCH_SIZE = 32
MODEL_PATH = 'lion_sight_2_model.pth'  
USE_GPU = torch.cuda.is_available()
# =============== #

device = torch.device("cuda" if USE_GPU else "cpu")
print(f"Using device: {device}")

# === Load MobileNetV2 and Modify === #
print("Loading MobileNetV2 model...")
model = models.mobilenet_v2(pretrained=True)
model.classifier = nn.Sequential(
    nn.Linear(model.last_channel, 512),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(512, 1),
)

# === Load existing trained weights === #
if os.path.exists(MODEL_PATH):
    print(f"Loading model weights from: {MODEL_PATH}")
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
else:
    print(f"WARNING: {MODEL_PATH} not found. Starting from scratch.")

model.to(device)

# === Optional: Freeze feature extractor if you only want to train classifier === #
# for param in model.features.parameters():
#     param.requires_grad = False

# === Set up optimizer === #
optimizer = optim.Adam(model.parameters(), lr=0.001)

# === Define transform === #
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225])
])

# === Load full dataset from a single directory === #
full_dataset = datasets.ImageFolder(root=TRAIN_DIRECTORY, transform=transform)

# === Split into train and validation subsets === #
# Get image paths and labels
samples = full_dataset.samples
filepaths, labels = zip(*samples)

train_idx, val_idx = train_test_split(
    list(range(len(labels))),
    stratify=labels,
    test_size=0.2,
)

# Subset datasets
train_dataset = Subset(full_dataset, train_idx)
validation_dataset = Subset(full_dataset, val_idx)

# === Account for class imbalance === #
# Count class labels only in the training split
train_targets = [full_dataset.samples[i][1] for i in train_dataset.indices]
counts = Counter(train_targets)
total = sum(counts.values())
class_weights = [total / counts[i] for i in range(len(counts))]
print(f"Class weights (based on training split): {class_weights}")

weights_tensor = torch.tensor(class_weights, dtype=torch.float).to(device)
criterion = nn.BCEWithLogitsLoss(pos_weight=weights_tensor[1])


# Turn into tensor
weights_tensor = torch.tensor(class_weights, dtype=torch.float).to(device)

# Then use in your function:
criterion = nn.BCEWithLogitsLoss(pos_weight=weights_tensor[1])  # Only applies to positive class

# === Data loaders === #
train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
validation_loader = DataLoader(validation_dataset, batch_size=BATCH_SIZE, shuffle=False)

# === Check split === #
print(f"Train samples: {len(train_dataset)} | Validation samples: {len(validation_dataset)}")
train_labels = [full_dataset.samples[i][1] for i in train_dataset.indices]
print("Training set class counts:", Counter(train_labels))

# === Training loop with KeyboardInterrupt handling === #
try:
    for epoch in range(NUM_EPOCHS):
        model.train()
        running_loss = 0.0
        progress_bar = tqdm(train_loader, desc=f"Epoch [{epoch + 1}/{NUM_EPOCHS}]")

        for images, labels in progress_bar:
            images, labels = images.to(device), labels.to(device)
            labels = labels.view(-1, 1)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels.float())
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            progress_bar.set_postfix(loss=(running_loss / len(train_loader)))
        
        print(f"Epoch [{epoch + 1}/{NUM_EPOCHS}], Loss: {running_loss / len(train_loader):.4f}")
except KeyboardInterrupt:
    print("\nTraining interrupted. Saving current model state...")
    torch.save(model.state_dict(), 'lion_sight_2_model_interrupted.pth')
    print("Model saved as lion_sight_2_model_interrupted.pth")

# === Validation loop === #
model.eval()
running_corrects = 0
running_loss = 0.0

with torch.no_grad():
    progress_bar = tqdm(validation_loader, desc="Validation")
    for images, labels in progress_bar:
        images, labels = images.to(device), labels.to(device)
        labels = labels.view(-1, 1)

        outputs = model(images)
        loss = criterion(outputs, labels.float())
        running_loss += loss.item()

        probs = torch.sigmoid(outputs)
        preds = (probs > 0.5).float()
        running_corrects += int(torch.sum(preds == labels).item())

        progress_bar.set_postfix(loss=(running_loss / len(validation_loader)))

    epoch_loss = running_loss / len(validation_loader)
    epoch_acc = running_corrects / len(validation_dataset)

    print(f"Validation Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.4f}")

# === Save fine-tuned model === #
torch.save(model.state_dict(), 'lion_sight_2_model_p2.pth')
print("Fine-tuned model saved as lion_sight_2_model_p2.pth")
