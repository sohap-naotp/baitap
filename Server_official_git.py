import os
import cv2
import socket
import pickle
import struct
import numpy as np
from transformers import AutoProcessor, AutoModelForCausalLM, AutoTokenizer, AutoModelForSeq2SeqLM
from paddleocr import PaddleOCR
from vietocr.tool.predictor import Predictor
from vietocr.tool.config import Cfg
from PIL import Image, ImageFont
from datetime import datetime
import multiprocessing as mp

server_ip = '192.168.1.8'
server_port = 8888

# Thiết lập biến môi trường
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Tải mô hình GIT để tạo caption
processor = AutoProcessor.from_pretrained("microsoft/git-base")
model_git = AutoModelForCausalLM.from_pretrained("microsoft/git-base")

# Tải mô hình dịch mBART-50 và tokenizer để dịch từ tiếng Anh sang tiếng Việt
translation_model = AutoModelForSeq2SeqLM.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")
translation_tokenizer = AutoTokenizer.from_pretrained("facebook/mbart-large-50-many-to-many-mmt")

# Cấu hình PaddleOCR và VietOCR
ocr = PaddleOCR(use_angle_cls=True, lang='ch')
config = Cfg.load_config_from_name('vgg_transformer')
config['device'] = 'cpu'
detector = Predictor(config)
font = ImageFont.truetype("arial.ttf", 12)

# Biến lưu trạng thái hiện tại của mô hình (0: GIT, 1: VietOCR)
current_model = mp.Value('i', 0)

# Hàm sinh mô tả từ hình ảnh bằng GIT
def generate_caption_git(frame):
    image = Image.fromarray(frame).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")
    output = model_git.generate(**inputs)
    caption_en = processor.decode(output[0], skip_special_tokens=True)
    print("English Caption:", caption_en)

    # Dịch từ tiếng Anh sang tiếng Việt với mBART-50
    translation_tokenizer.src_lang = "en_XX"
    translation_inputs = translation_tokenizer(caption_en, return_tensors="pt")
    translation_inputs["forced_bos_token_id"] = translation_tokenizer.lang_code_to_id["vi_VN"]
    translated_output = translation_model.generate(**translation_inputs)
    caption_vi = translation_tokenizer.decode(translated_output[0], skip_special_tokens=True)
    return caption_vi

# Hàm xử lý frame bằng OCR
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
                    result_text = detector.predict(Image.fromarray(img_crop), return_prob=False)
                    full_text += result_text + " "
    return full_text if full_text else "Không phát hiện văn bản"

# Hàm xử lý client
def handle_client(client_socket, current_model):
    try:
        while True:
            command = client_socket.recv(1).decode('utf-8')
            if command == '1':
                print('Start:', datetime.now())
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
                    response_text = generate_caption_git(frame)
                elif current_model.value == 1:
                    response_text = process_frame_ocr(frame)
                print(f"Detected: {response_text}")
                client_socket.send(response_text.encode('utf-8'))

            elif command == '2':
                with current_model.get_lock():
                    current_model.value = 1 if current_model.value == 0 else 0
                model_name = "OCR" if current_model.value == 1 else "GIT"
                print(f"Switched to {model_name}")
                client_socket.send(f"Switched to {model_name}".encode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

# Lắng nghe kết nối
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
