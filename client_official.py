import socket
import cv2
import pickle
import struct
import RPi.GPIO as GPIO
import time
import threading
from gtts import gTTS
from io import BytesIO
from pygame import mixer
from datetime import datetime

# GPIO Pin setup
BUTTON_SEND_PIN = 17
BUTTON_SWITCH_PIN = 27

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_SEND_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_SWITCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Socket setup
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
host_ip = '192.168.1.4'  # Thay d?i IP cho phÃ¹ h?p v?i d?a ch? IP c?a server
port = 8888
client_socket.connect((host_ip, port))

# Camera setup
camera = cv2.VideoCapture(0)

# Initialize pygame mixer to play audio from memory
mixer.init()

# Function to convert text to speech using gTTS and play from memory
def play_response(response_text):
    try:
        tts = gTTS(text=response_text, lang='vi')
        audio_data = BytesIO()
        tts.write_to_fp(audio_data)
        audio_data.seek(0)

        mixer.music.load(audio_data)
        mixer.music.play()

        while mixer.music.get_busy():
            time.sleep(0.1)
    except Exception as e:
        print(f"Error with TTS: {e}")

# Function to send detection command to the server
def send_detection_command():
    print('Start', datetime.now())
    try:
        ret, frame = camera.read()
        if not ret:
            print("KhÃ´ng th? d?c frame t? camera.")
            return

        frame = cv2.resize(frame, (640, 480))
        data = pickle.dumps(frame)
        message_size = struct.pack("Q", len(data))

        print('Send', datetime.now())

        client_socket.sendall(b'1' + message_size + data)

        response_text = client_socket.recv(1024).decode('utf-8')
        print(f"Server response: {response_text}", datetime.now())

        play_response(response_text)  # Chuy?n van b?n thÃ nh gi?ng nÃ³i vÃ  phÃ¡t
    except Exception as e:
        print(f"Error: {e}")

# Function to switch model between YOLO and OCR
def switch_model():
    try:
        client_socket.sendall(b'2')  # G?i l?nh chuy?n d?i model
        response = client_socket.recv(1024).decode('utf-8')
        print(f"Server response: {response}")
        play_response(response)  # PhÃ¡t Ã¢m ph?n h?i t? server
    except Exception as e:
        print(f"Error switching model: {e}")

# Monitor buttons for input
def monitor_buttons():
    try:
        while True:
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

# Function to display camera frames
def read_cam():
    try:
        while True:
            ret, frame = camera.read()
            if not ret:
                print("KhÃ´ng th? d?c frame t? camera.")
                break

            frame = cv2.resize(frame, (640, 480))
            cv2.imshow('Client Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
        cv2.destroyAllWindows()

# Start threads to monitor buttons and display camera frames
monitor_buttons_thread = threading.Thread(target=monitor_buttons)
read_cam_thread = threading.Thread(target=read_cam)
monitor_buttons_thread.start()
read_cam_thread.start()

monitor_buttons_thread.join()
read_cam_thread.join()

