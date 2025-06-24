from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Convolution2D, MaxPool2D, Flatten, Dense
import cv2
from keras.preprocessing.image import load_img, img_to_array
import numpy as np


cap = cv2.VideoCapture(0)

detector = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
det = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_profileface.xml')

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame = cv2.flip(frame, 1)
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces_frontal = detector.detectMultiScale(img, scaleFactor=1.3, minNeighbors=5)
    faces_profile = det.detectMultiScale(img, scaleFactor=1.3, minNeighbors=5)

    for (x, y, w, h) in faces_frontal:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    for (x, y, w, h) in faces_profile:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 255), 2)

    if len(faces_frontal) > 0 or len(faces_profile) > 0:
        cv2.imwrite('detected_face.jpg', frame)
        print("Image saved")

    cv2.imshow('Video', frame)

    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()