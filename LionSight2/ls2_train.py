import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from tqdm import tqdm # type: ignore
from torchvision import transforms, datasets, models # type: ignore

TRAIN_DIRECTORY = './lion_sight_2/training_data'
VALIDATION_DIRECTORY = './lion_sight_2/validation_data'
NUM_EPOCHS = 10

print("Loading MobileNetV2 model...")
model = models.mobilenet_v2(pretrained=True)
model.classifier = nn.Sequential(
    nn.Linear(model.last_channel, 512),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(512, 1),
)

criterion = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])

if torch.cuda.is_available():
    print("CUDA is available. Using GPU.")
    device = torch.device("cuda")
else:
    print("CUDA is not available. Using CPU.")
    device = torch.device("cpu")
model.to(device)

# Load the dataset
train_dataset = datasets.ImageFolder(root=TRAIN_DIRECTORY, transform=transform)
train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)

# Load the validation dataset
validation_dataset = datasets.ImageFolder(root=VALIDATION_DIRECTORY, transform=transform)
validation_loader = DataLoader(validation_dataset, batch_size=32, shuffle=False)

# Training loop
for epoch in range(NUM_EPOCHS):
    model.train()
    running_loss = 0.0
    progress_bar = tqdm(train_loader, desc=f"Epoch [{epoch + 1}/{NUM_EPOCHS}]")
    for images, labels in progress_bar:
        images, labels = images.to(device), labels.to(device)

        # Reshape labels to match the output shape
        labels = labels.view(-1, 1)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels.float())
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
        progress_bar.set_postfix(loss=(running_loss / len(train_loader)))
    
    print(f"Epoch [{epoch + 1}/{NUM_EPOCHS}], Loss: {running_loss / len(train_loader):.4f}")

# Validation loop
model.eval()
running_corrects = 0
running_loss = 0.0

with torch.no_grad():
    progress_bar = tqdm(validation_loader, desc="Validation")
    for images, labels in progress_bar:
        images, labels = images.to(device), labels.to(device)

        # Reshape labels to match the output shape
        labels = labels.view(-1, 1)

        outputs = model(images)
        loss = criterion(outputs, labels.float())

        running_loss += loss.item()

        predictions = torch.round(outputs)
        running_corrects += torch.sum(predictions == labels.data.view_as(predictions)).item() # type: ignore

        progress_bar.set_postfix(loss=(running_loss / len(validation_loader)))

    epoch_loss = running_loss / len(validation_loader)
    epoch_acc = running_corrects / len(validation_dataset)

    print(f"Validation Loss: {epoch_loss:.4f}, Accuracy: {epoch_acc:.4f}")


# Save the model
torch.save(model.state_dict(), 'lion_sight_2_model.pth')
print("Model saved as lion_sight_2_model.pth")