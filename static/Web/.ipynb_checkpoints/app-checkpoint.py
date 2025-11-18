import tensorflow as tf
from flask import Flask, render_template, request, redirect,send_file,Response, url_file
from ultralytics import YOLO



model = YOLO('best.pt')

results = model(['image/test/1.jpg','image/test/2.jpg'])
for result in results:
    boxes = result.boxes  # Boxes object for bounding box outputs
    masks = result.masks  # Masks object for segmentation masks outputs
    keypoints = result.keypoints  # Keypoints object for pose outputs
    probs = result.probs  # Probs object for classification outputs
    obb = result.obb  # Oriented boxes object for OBB outputs
    result.show()  # display to screen
    result.save(filename="result.jpg")  # save to disk