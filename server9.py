import socket
import cv2
import pickle
import struct
import multiprocessing as mp
from ultralytics import YOLO
import pytesseract
import pyttsx3

# Thiết lập Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Đường dẫn đến tesseract

server_ip = '192.168.1.11'
server_port = 8888

# Khởi tạo mô hình YOLOv8
model_yolo = YOLO('yolov8n.pt')
current_model = 'yolo'

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

def handle_client(client_socket, frame_queue, result_queue):
    global current_model
    try:
        while True:
            # Nhận lệnh từ client
            command = client_socket.recv(1).decode('utf-8')
            if command == '1':
                frame = frame_queue.get()
                if frame is not None:
                    response_text = ""
                    if current_model == 'yolo':
                        response_text = process_frame_yolo(frame)
                    elif current_model == 'ocr':
                        response_text = process_frame_ocr(frame)
                    print(f"Detected: {response_text}")
                    result_queue.put(response_text)
                    client_socket.send(response_text.encode('utf-8'))
            elif command == '2':
                current_model = 'ocr' if current_model == 'yolo' else 'yolo'
                print(f"Switched to {current_model}")
                client_socket.send(f"Switched to {current_model}".encode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def update_frame(frame_queue):
    # Khởi tạo camera trong hàm update_frame
    camera = cv2.VideoCapture(0)
    while True:
        ret, frame = camera.read()
        if ret:
            frame_queue.put(frame)
            cv2.imshow('Server Frame', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    camera.release()
    cv2.destroyAllWindows()

def listen_socket(server_socket, frame_queue, result_queue):
    while True:
        client_socket, addr = server_socket.accept()
        print(f"Got connection from: {addr}")
        handle_client(client_socket, frame_queue, result_queue)

if __name__ == '__main__':
    # Thiết lập server socket với SO_REUSEADDR
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)
    print(f"LISTENING AT: {server_socket.getsockname()}")

    frame_queue = mp.Queue()
    result_queue = mp.Queue()

    # Tạo các process
    p1 = mp.Process(target=update_frame, args=(frame_queue,))
    p2 = mp.Process(target=listen_socket, args=(server_socket, frame_queue, result_queue))

    # Chạy các process
    p1.start()
    p2.start()

    p1.join()
    p2.join()
