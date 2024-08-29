import os
import cv2
import socket
import pickle
import struct
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from transformers import MarianMTModel, MarianTokenizer
from paddleocr import PaddleOCR
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
import multiprocessing as mp

server_ip = '192.168.1.11'
server_port = 8888

# Thiết lập biến môi trường
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Tải model BLIP
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

# Tải model dịch sang tiếng Việt
translation_tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-en-vi")
translation_model = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-en-vi")

# Cấu hình PaddleOCR và vietocr
ocr = PaddleOCR(use_angle_cls=True, lang='ch')
config = Cfg.load_config_from_name('vgg_transformer')  # sử dụng config mặc định của vietocr
config['device'] = 'cpu'  # device chạy 'cuda:0', 'cuda:1', 'cpu'
detector = Predictor(config)

def process_frame_blip(frame):
    image = Image.fromarray(frame)
    inputs = processor(images=image, return_tensors="pt")
    output = model.generate(**inputs)
    caption = processor.decode(output[0], skip_special_tokens=True)
    
    translated = translation_model.generate(**translation_tokenizer(caption, return_tensors="pt", padding=True))
    translated_caption = translation_tokenizer.decode(translated[0], skip_special_tokens=True)
    
    return translated_caption

def process_frame_ocr(frame):
    results = ocr.ocr(frame, cls=True)
    full_text = ""
    if results:
        for line in results:
            if line:
                for li in line:
                    list_x, list_y = [], []
                    for i in li[0]:
                        list_x.append(i[0])
                        list_y.append(i[1])
                    xmin = int(min(list_x))
                    ymin = int(min(list_y))
                    xmax = int(max(list_x))
                    ymax = int(max(list_y))
                    h = ymax - ymin
                    xmin -= int(0.2 * h)
                    xmax += int(0.2 * h)
                    ymin -= int(0.1 * h)
                    ymax += int(0.1 * h)
                    img_crop = frame[ymin:ymax, xmin:xmax]
                    img_crop = Image.fromarray(img_crop)
                    result_text = detector.predict(img_crop, return_prob=False)
                    full_text += result_text + " "
    return full_text if full_text else "Không phát hiện văn bản"

def handle_client(client_socket, current_model):
    try:
        while True:
            # Nhận lệnh từ client
            command = client_socket.recv(1).decode('utf-8')

            if command == '1':
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

                cv2.imshow('Server Frame', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

                response_text = ""
                if current_model.value == 0:
                    response_text = process_frame_blip(frame)
                elif current_model.value == 1:
                    response_text = process_frame_ocr(frame)
                client_socket.send(response_text.encode('utf-8'))
            elif command == '2':
                with current_model.get_lock():
                    current_model.value = 1 if current_model.value == 0 else 0
                model_name = "OCR" if current_model.value == 1 else "BLIP"
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
