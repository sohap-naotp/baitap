import socket
import cv2
import pickle
import struct
import pyttsx3
import RPi.GPIO as GPIO
import time
import threading
from datetime import datetime

BUTTON_SEND_PIN = 17
BUTTON_SWITCH_PIN = 27
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_SEND_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.1.11'
port = 8888
client_socket.connect((host_ip, port))

engine = pyttsx3.init()
engine.setProperty('voice', 'vietnam+f1')

camera = cv2.VideoCapture(0)

def send_detection_command():
    print('Start', datetime.now())
    try:
        ret, frame = camera.read()
        if not ret:
            print("Khng th? d?c frame t? camera.")
            return

        frame = cv2.resize(frame, (640, 480))
        #cv2.imshow('Client Frame', frame)
        #if cv2.waitKey(1) & 0xFF == ord('q'):
        #    return

        data = pickle.dumps(frame)
        message_size = struct.pack("Q", len(data))
        
        print('Send', datetime.now())

        client_socket.sendall(b'1' + message_size + data)

        response_text = client_socket.recv(1024).decode('utf-8')
        print(f"Server response: {response_text}", datetime.now())

        engine.say(response_text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error: {e}")

def switch_model():
    try:
        client_socket.send(b'2')
        response = client_socket.recv(1024).decode('utf-8')
        print(response)
    except Exception as e:
        print(f"Error: {e}")

def monitor_buttons():
    try:
        while True:
            #send_detection_command()
            #time.sleep(3)
            if GPIO.input(BUTTON_SEND_PIN) == GPIO.LOW:
                print("Send button pressed, sending detection command to server...")
                send_detection_command()
                time.sleep(1)

            if GPIO.input(BUTTON_SWITCH_PIN) == GPIO.LOW:
                print("Switch button pressed, switching model...")
                switch_model()
                time.sleep(1)

    except KeyboardInterrupt:
        GPIO.cleanup()
        camera.release()
        client_socket.close()
def read_cam():
    while True:
        ret, frame = camera.read()
        if not ret:
            print("Khng th? d?c frame t? camera.")
            return

        frame = cv2.resize(frame, (640, 480))
        cv2.imshow('Client Frame', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
	
monitor_buttons_thread = threading.Thread(target=monitor_buttons)
read_cam_thread = threading.Thread(target=read_cam)
monitor_buttons_thread.start()
read_cam_thread.start()

monitor_buttons_thread.join()
read_cam_thread.join()
