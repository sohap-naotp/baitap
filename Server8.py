import socket
import cv2
import pickle
import struct
from ultralytics import YOLO
import pytesseract
import pyttsx3
import threading
import multiprocessing as mp
from datetime import datetime

# Thiết lập Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

server_ip = '192.168.1.11'
server_port = 8888

# Khởi tạo mô hình YOLOv8
model_yolo = YOLO('yolov8n.pt')
current_model = mp.Value('i', 0)  # 0 for YOLO, 1 for OCR

# Khởi tạo pyttsx3 cho Text-to-Speech với tiếng Việt
engine = pyttsx3.init()
engine.setProperty('voice', 'vietnam+f1')

def process_frame_yolo(frame):
    results = model_yolo(frame)
    detected_objects = [model_yolo.names[int(box.cls[0])] for result in results for box in result.boxes]
    return ", ".join(detected_objects) if detected_objects else "Không phát hiện vật thể"

def process_frame_ocr(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray, lang='vie')
    return text.strip() if text else "Không phát hiện văn bản"

def handle_client(client_socket, current_model):
    try:
        while True:
            # Nhận lệnh từ client
           
            command = client_socket.recv(1).decode('utf-8')

            if command == '1':
                print('Start:', datetime.now())
                # Nhận frame từ client
                data = b""
                payload_size = struct.calcsize("Q")

                while len(data) < payload_size:
                    packet = client_socket.recv(4 * 1024)
                    if not packet:
                        return
                    data += packet

                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]

                while len(data) < msg_size:
                    data += client_socket.recv(4 * 1024)

                frame_data = data[:msg_size]
                frame = pickle.loads(frame_data)

                # Hiển thị frame trên server
                print('Show:', datetime.now())
                cv2.imshow('Server Frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                response_text = ""
                if current_model.value == 0:
                    response_text = process_frame_yolo(frame)
                elif current_model.value == 1:
                    response_text = process_frame_ocr(frame)
                print('Finish:', datetime.now())
                print(f"Detected: {response_text}")
                client_socket.send(response_text.encode('utf-8'))
            elif command == '2':
                with current_model.get_lock():
                    current_model.value = 1 if current_model.value == 0 else 0
                model_name = "OCR" if current_model.value == 1 else "YOLO"
                print(f"Switched to {model_name}")
                client_socket.send(f"Switched to {model_name}".encode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def listen_socket(server_socket, current_model):
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Got connection from: {addr}")
        client_process = mp.Process(target=handle_client, args=(client_socket, current_model))
        client_process.start()

if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)
    print(f"LISTENING AT: {server_socket.getsockname()}")

    current_model = mp.Value('i', 0)
    p = mp.Process(target=listen_socket, args=(server_socket, current_model))
    p.start()
    p.join()

    cv2.destroyAllWindows()
