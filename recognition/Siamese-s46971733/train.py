# Imports
import time
import torch
from torch.utils.data import Dataset
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torchvision.transforms as transforms
import matplotlib.pyplot as plt
import cv2
import os
from dataset import get_dataset
from modules import Resnet, Resnet34, classifier, Resnet3D, Resnet3D_34
from sklearn.manifold import TSNE
import seaborn as sns
import numpy as np

# Select a100.
# squeue.

# Toggles.
all_train = 1   # If 0 Disables all training.
train = 0       # Enables/Disables Resnet Training
train_clas = 0  # Enables/Disables Classifier Training
test = 1        # Enables/Disables testing.
plot_loss = 0   # Enables/Disables plotting of loss.
data_visual = 1 # Enables/Disables Visualisation of Data

# Path that model is saved to and loaded from.
PATH = 'resnet_net_1000.pth'
CLAS_PATH = 'clas_net_neww.pth'

# Path that plots are saved to.
PLOT_PATH = 'training_loss_temp.png'
DATA_PATH = 'data_plot_temp.png'

# Hyperparameters
num_epochs = 50
num_epochs_clas = 10
batch_size = 10
batch_size_clas = 20
learning_rate = 0.001
res_learning_rate = 0.001


device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if not torch.cuda.is_available():
    print("No CUDA Found. Using CPU")

print("\n")

# Datasets and Dataloaders
trainset = get_dataset(train=1, clas=0)

testset = get_dataset(train=0, clas=0)
trainset_clas = get_dataset(train=1, clas=1)

validset = get_dataset(valid=1, clas=0)
validset_clas = get_dataset(valid=1, clas=1)


trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size, shuffle=True)

testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size_clas, shuffle=False)
validloader = torch.utils.data.DataLoader(validset, batch_size=batch_size, shuffle=False)

trainloader_clas = torch.utils.data.DataLoader(trainset_clas, batch_size=batch_size_clas, shuffle=True)

trainloader_tsne= torch.utils.data.DataLoader(trainset_clas, batch_size=len(trainloader_clas.dataset), shuffle=True)

for i, data in enumerate(trainloader_tsne, 0):
    features_tsne = data[0].to(device)
    labels_tsne = data[1].to(device).cpu().numpy()


validloader_clas = torch.utils.data.DataLoader(validset_clas, batch_size=batch_size_clas, shuffle=False)

# Model.
#resnet = Resnet().to(device)
resnet = Resnet3D().to(device)
#resnet = Resnet3D_34().to(device)
clas_net = classifier().to(device)

# Optimizer

criterion = nn.TripletMarginLoss(margin=1)
#criterion_class = nn.CrossEntropyLoss()
criterion_class = nn.BCEWithLogitsLoss()
optimizer = optim.Adam(resnet.parameters(), lr=res_learning_rate, weight_decay=0.0001)
class_optimizer = optim.Adam(clas_net.parameters(), lr=learning_rate)

# Future spot for Scheduler?



#

if train == 0:
    print("Training was disabled. \nLoading net model from path.")
    resnet.load_state_dict(torch.load(PATH))
if train_clas == 0:
    print("Classifier Training was disabled. \nLoading classifier from path.")
    clas_net.load_state_dict(torch.load(CLAS_PATH))


loss_list = []
valid_loss_list = []
class_loss_list = []
valid_class_loss_list = []

if all_train == 1:
    # Start timing.
    st = time.time()

    ##################################
    # Resnet Training - Triplet Loss #
    ##################################

    if train == 1:
        resnet.train()
        print(f">>> Training \n")

        for epoch in range(num_epochs):
            running_loss = 0.0
            val_running_loss = 0.0

            # Training
            # Loop over every batch in data loader.
            for i, data in enumerate(trainloader, 0):
                # Extract data and transfer to GPU.
                anchor = data[0].to(device)
                positive = data[1].to(device)
                negative = data[2].to(device)

                # Zero the gradients -- Ensuring gradients not accumulated
                #                       across multiple training iterations.
                optimizer.zero_grad()

                # Forward Pass
                anchor_out = resnet(anchor)
                positive_out = resnet(positive)
                negative_out = resnet(negative)

                #print(f"Sizes are {anchor_out.shape}, {positive_out.shape}, {negative_out.shape}")

                # Calculate Loss with Triplet Loss.
                loss = criterion(anchor_out, positive_out, negative_out)

                # Compute gradient with respect to model.
                loss.backward()

                # Optimizer step - Update model parameters.
                optimizer.step()

                # Keep track of running loss.
                running_loss += loss.item()

                # Print Loss Info while training.
                if (i + 1) % 1 == 0:
                    print(f'[T][Epoch {epoch + 1}/{num_epochs}, {i + 1:5d}] - Loss: {running_loss:.5f}')
                    #print(f"[T] Anchor Size is: {anchor.size(dim=0)}, Divided: {loss / anchor.size(dim=0)}")
                    running_loss = 0.0

                loss_list.append(loss.item())

            # Validation
            print(">>Validating")
            resnet.eval()

            # Evaluating - Gradient doesn't change.
            with torch.no_grad():
                # Loop over every batch in data loader.
                for i, data in enumerate(validloader, 0):
                    # Extract data and transfer to GPU.
                    anchor = data[0].to(device)
                    positive = data[1].to(device)
                    negative = data[2].to(device)

                    # Zero the gradients -- Ensuring gradients not accumulated
                    #                       across multiple training iterations.
                    optimizer.zero_grad()

                    # Forward Pass
                    anchor_out = resnet(anchor)
                    positive_out = resnet(positive)
                    negative_out = resnet(negative)

                    # Calculate Loss with Triplet Loss.
                    loss = criterion(anchor_out, positive_out, negative_out)

                    # Keep track of running loss.
                    val_running_loss += loss.item()
                    total_loss = val_running_loss/anchor.size(dim=0)

                    # Print Loss Info while training.
                    if (i + 1) % 1 == 0:
                        print(f'[V][Epoch {epoch + 1}/{num_epochs}, {i + 1:5d}] - Loss: {val_running_loss:.5f}')
                        print(f"[V] Anchor Size is: {anchor.size(dim=0)}, Divided: {loss / anchor.size(dim=0)}")
                        val_running_loss = 0.0

                    #valid_loss_list.append(loss.item())
                    valid_loss_list.append(total_loss)


        # Save trained model for later use.
        torch.save(resnet.state_dict(), PATH)
        print(f"\nModel Saved at {PATH}...")

    #######################################
    # Resnet Data Visualisation with TSNE #
    #######################################

    if data_visual == 1:
        for param in resnet.parameters():
            param.requires_grad = False

        label_map = {0: "NC", 1: "AD"}
        features_tsne1 = resnet(features_tsne)

        train_tsne = TSNE().fit_transform(features_tsne1.cpu())

        print(train_tsne[: 0])

        plt.figure()
        sns.scatterplot(
            x=train_tsne[:, 0],
            y=train_tsne[:, 1],

            hue=[label_map[i] for i in labels_tsne])

        plt.title("training")
        plt.legend()
        plt.savefig(DATA_PATH)
        plt.show()

    #######################
    # Classifier Training #
    #######################

    if train_clas == 1:
        # Freeze Resnet trained model.
        for param in resnet.parameters():
            param.requires_grad = False

        print(f"\n>>> Training Classifier \n")
        # Start timing.
        class_st = time.time()
        for epoch in range(num_epochs_clas):
            running_loss = 0.0

            clas_net.train()
            #resnet.eval()



            # Loop over every batch in data loader.
            for i, (inputs, labels) in enumerate(trainloader_clas, 0):
                # Extract data and transfer to GPU.
                inputs = inputs.to(device)
                labels = labels.to(device, dtype=torch.float)
                #labels = data[1].to(device)  # For Cross Entropy Loss
                # labels = torch.stack([data[1]], dim=1).float().to(device)  # For Binary Cross Entropy Loss
                print(labels)
                # Zero the gradients -- Ensuring gradients not accumulated
                #                       across multiple training iterations.
                class_optimizer.zero_grad()

                # Forward Pass
                res_output = resnet(inputs)
                output = clas_net(res_output).squeeze()

                # Calculate Loss with Cross Entropy.
                loss = criterion_class(output, labels)

                # Compute gradient with respect to model.
                loss.backward()

                # Optimizer step - Update model parameters.
                class_optimizer.step()

                print(loss)

                # Keep track of running loss.
                running_loss += loss.item()

                # Print Loss Info while training.
                if (i + 1) % 1 == 0:
                    print(f'[Training Classifier][Epoch {epoch + 1}/{num_epochs_clas}, {i + 1:5d}] - Loss: {running_loss / 1:.5f}')
                    running_loss = 0.0

                class_loss_list.append(loss.item())

        # Save trained model for later use.
        torch.save(clas_net.state_dict(), CLAS_PATH)

    print(">>> Training Finished.")
    elapsed = time.time() - st
    print(f"\nTraining took: {elapsed}s to complete, or {elapsed/60} minutes.\n")

if test == 1:
    print(">>> Testing Start")

    # Start timing.
    st = time.time()

    # Set Model to evaluation mode.
    #resnet.eval()
    clas_net.eval()

    # Gradient not required, improves performance.
    with torch.no_grad():
        correct = 0.0
        total = 0.0

        for i, data in enumerate(testloader, 0):
            inputs, labels = data[0].to(device), data[1].to(device)

            features = resnet(inputs)

            #print(f"Tensors: {features[0]}, {features[1]}")



            output = clas_net(features)


            #print(f"Output is: {output}, {output[0]==output[1]}")
            #print(f"Softmax is: {torch.softmax(output, dim=1)}")

            #predicted = torch.softmax(output, dim=1).argmax(dim=1)
            print(f"Output is {output}")
            predicted = torch.round(torch.sigmoid(output))
            print(f"After Sigmoid is {predicted}")

            # For each image in the batch -> as .size is [batch, channel, height, width]
            for index in range(inputs.size(0)):
                pred = predicted[index].cpu()
                true_val = labels[index].cpu()

                #print(f"Predicted is {pred}, True is {true_val}")

                # Calculate dice coefficient and append to list.
                if pred == true_val:
                    correct += 1

                total += 1

        accuracy = correct/total

        print(f"Accuracy of the Model is {accuracy*100}%")


# Plot the loss over the many iterations of training.
if plot_loss == 1:
    plt.figure(figsize=(8, 12))
    plt.subplot(3, 1, 1)
    plt.title("Resnet Loss")
    plt.plot(loss_list)
    plt.xlabel("Iterations")
    plt.ylabel("Loss")

    plt.subplot(3, 1, 2)
    plt.title("Validation Resnet Loss")
    plt.plot(valid_loss_list)
    plt.xlabel("Iterations")
    plt.ylabel("Loss")

    plt.subplot(3, 1, 3)
    plt.title("Classifier Loss")
    plt.plot(class_loss_list)
    plt.xlabel("Iterations")
    plt.ylabel("Loss")

    plt.tight_layout()
    plt.savefig(PLOT_PATH)
    plt.show()
