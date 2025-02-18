# -*- coding: utf-8 -*-
"""frcnn_pytch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1576n8tP0hfvmZ21WWGPD6sf7H0LbQsl1
"""

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %%shell
# pip install cython
# # Install pycocotools, the version by default in Colab
# # has a bug fixed in https://github.com/cocodataset/cocoapi/pull/354
# pip install -U 'git+https://github.com/cocodataset/cocoapi.git#subdirectory=PythonAPI'

import os
import numpy as np
import torch
import torch.utils.data
from PIL import Image

class charDataset(object):
    def __init__(self, root, transforms=None):
        self.root = root
        self.transforms = transforms
        # load all image files, sorting them to
        # ensure that they are aligned
        self.imgs = list(sorted(os.listdir(os.path.join(root, "image"))))
        self.masks = list(sorted(os.listdir(os.path.join(root, "label"))))

    def __getitem__(self, idx):
        # load images ad masks
        img_path = os.path.join(self.root, "image", self.imgs[idx])

        mask_path = os.path.join(self.root, "label", self.masks[idx])

        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        img = img.convert("RGB")
        # note that we haven't converted the mask to RGB,
        # because each color corresponds to a different instance
        # with 0 being background

        # get bounding box coordinates for each mask
        num_objs = 0
        boxes = []
        with open(mask_path) as f:
          for line in f:
            num_objs += 1
            xc, yc, ws, hs = list(map(float, line.split()[1:]))
            x1 = (xc-ws/2)*w
            y1 = (yc-hs/2)*h
            boxes.append([x1, y1, x1+ws*w, y1+hs*h])

        # convert everything into a torch.Tensor
        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        # there is only one class
        labels = torch.ones((num_objs,), dtype=torch.int64)

        # masks = torch.as_tensor(masks, dtype=torch.uint8)

        image_id = torch.tensor([idx])
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])
        # suppose all instances are not crowd
        iscrowd = torch.zeros((num_objs,), dtype=torch.int64)

        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        # target["masks"] = masks
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd

        if self.transforms is not None:
            img, target = self.transforms(img, target)

        return img, target

    def __len__(self):
        return len(self.imgs)

dataset = charDataset('/content/drive/My Drive/bbox_data/')
dataset[0]

import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
 
# load a model pre-trained pre-trained on COCO
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
 
# replace the classifier with a new one, that has
# num_classes which is user-defined
num_classes = 2  # 1 class (person) + background
# get number of input features for the classifier
in_features = model.roi_heads.box_predictor.cls_score.in_features
# replace the pre-trained head with a new one
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

# load a model pre-trained pre-trained on COCO
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)

# replace the classifier with a new one, that has
# num_classes which is user-defined
num_classes = 2  # 1 class (person) + background
# get number of input features for the classifier
in_features = model.roi_heads.box_predictor.cls_score.in_features
# replace the pre-trained head with a new one
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

# Commented out IPython magic to ensure Python compatibility.
# %%shell
# 
# # Download TorchVision repo to use some files from
# # references/detection
# git clone https://github.com/pytorch/vision.git
# cd vision
# git checkout v0.3.0
# 
# cp references/detection/utils.py ../
# cp references/detection/transforms.py ../
# cp references/detection/coco_eval.py ../
# cp references/detection/engine.py ../
# cp references/detection/coco_utils.py ../

from engine import train_one_epoch, evaluate
import utils
import transforms as T


def get_transform(train):
    transforms = []
    # converts the image, a PIL image, into a PyTorch Tensor
    transforms.append(T.ToTensor())
    if train:
        # during training, randomly flip the training images
        # and ground-truth for data augmentation
        transforms.append(T.RandomHorizontalFlip(0.5))
    return T.Compose(transforms)

# use our dataset and defined transformations
dataset = charDataset('/content/drive/My Drive/bbox_data/', get_transform(train=True))
dataset_test = charDataset('/content/drive/My Drive/bbox_data/', get_transform(train=False))

# split the dataset in train and test set
torch.manual_seed(1)
indices = torch.randperm(len(dataset)).tolist()
dataset = torch.utils.data.Subset(dataset, indices[:-20])
dataset_test = torch.utils.data.Subset(dataset_test, indices[-20:])

# define training and validation data loaders
data_loader = torch.utils.data.DataLoader(
    dataset, batch_size=2, shuffle=True, num_workers=4,
    collate_fn=utils.collate_fn)

data_loader_test = torch.utils.data.DataLoader(
    dataset_test, batch_size=1, shuffle=False, num_workers=4,
    collate_fn=utils.collate_fn)

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

# our dataset has two classes only - background and person
num_classes = 2

# get the model using our helper function
# move model to the right device
model.to(device)

# construct an optimizer
params = [p for p in model.parameters() if p.requires_grad]
optimizer = torch.optim.SGD(params, lr=0.005,
                            momentum=0.9, weight_decay=0.0005)

# and a learning rate scheduler which decreases the learning rate by
# 10x every 3 epochs
lr_scheduler = torch.optim.lr_scheduler.StepLR(optimizer,
                                               step_size=3,
                                               gamma=0.1)

num_epochs = 10

for epoch in range(num_epochs):
    # train for one epoch, printing every 10 iterations
    train_one_epoch(model, optimizer, data_loader, device, epoch, print_freq=10)
    # update the learning rate
    lr_scheduler.step()
    # evaluate on the test dataset
    evaluate(model, data_loader_test, device=device)

"""save model"""

PATH = '/content/drive/My Drive/bbox_data/pytorchmodel/pytorchmodel'
torch.save(model, PATH)

"""load model"""

# model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)
model = torch.load(PATH)

# pick one image from the test set
image, _ = dataset_test[12]
# put the model in evaluation mode
model.eval()
with torch.no_grad():
    prediction = model([image.to(device)])

prediction[0]

from PIL import Image, ImageDraw
selected_boxes = prediction[0]["boxes"]
selected_scores = prediction[0]["scores"]
img = Image.fromarray(image.mul(255).permute(1, 2, 0).byte().numpy())
draw = ImageDraw.Draw(img)
#draw predictions:
for i in range(len(selected_scores)):
  draw.rectangle([(selected_boxes[i][0], selected_boxes[i][1]), (selected_boxes[i][2],  selected_boxes[i][3])],  outline ="red",  width = 3)
  draw.text((selected_boxes[i][1]*img.width, selected_boxes[i][0]*img.height), text = str(selected_scores[i]))
# draw groundtruth:
# 0ec93009-c6fe-4d9c-ae25-c1a8d9d2a1c
# for i in range(len(true_labels["xmin"].values)):
#   draw.rectangle([(true_labels["xmin"].values[i], true_labels["ymin"].values[i]), (true_labels["xmax"].values[i], true_labels["ymax"].values[i])],  outline ="green",  width = 3)
img