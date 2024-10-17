import RPi.GPIO as GPIO
import subprocess
import time

# GPIO Pin cho nÃºt báº¥m
BUTTON_GPIO = 22

# ÄÆ°á»ng dáº«n tá»›i mÃ´i trÆ°á»ng áº£o vÃ  cÃ¡c file Python
VENV_ACTIVATE = "/home/dung/si/bin/activate"
FILE1 = "/home/dung/send_gps_official.py"
FILE2 = "/home/dung/google_assistant_official.py"
FILE3 = "/home/dung/my_client_official.py"  

# Biáº¿n Ä‘á»ƒ lÆ°u trá»¯ script hiá»‡n táº¡i Ä‘ang cháº¡y
current_script = None
current_file = FILE1  # Báº¯t Ä‘áº§u vá»›i file Ä‘áº§u tiÃªn
files = [FILE1, FILE2, FILE3]  # Danh sÃ¡ch cÃ¡c file

# Biáº¿n Ä‘á»ƒ lÆ°u trá»¯ chá»‰ sá»‘ cá»§a file hiá»‡n táº¡i
current_file_index = 0

# HÃ m Ä‘á»ƒ dá»«ng script hiá»‡n táº¡i náº¿u Ä‘ang cháº¡y
def stop_current_script():
    global current_script
    if current_script is not None:
        print(f"Dá»«ng script: {files[current_file_index]}")
        current_script.terminate()
        current_script.wait()  # Äá»£i cho script dá»«ng hoÃ n toÃ n
        current_script = None

# HÃ m Ä‘á»ƒ cháº¡y má»™t script má»›i
def start_new_script(file_path):
    global current_script
    print(f"Cháº¡y script: {file_path}")
    current_script = subprocess.Popen(['bash', '-c', f'source {VENV_ACTIVATE} && python3 {file_path}'])

# HÃ m Ä‘á»ƒ chuyá»ƒn Ä‘á»•i giá»¯a cÃ¡c file Python
def switch_script():
    global current_file_index

    # Dá»«ng script hiá»‡n táº¡i trÆ°á»›c khi chuyá»ƒn Ä‘á»•i
    stop_current_script()

    # Chuyá»ƒn Ä‘á»•i sang file tiáº¿p theo trong danh sÃ¡ch
    current_file_index = (current_file_index + 1) % len(files)
    start_new_script(files[current_file_index])

# Cáº¥u hÃ¬nh GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Cháº¡y script Ä‘áº§u tiÃªn (FILE1)
start_new_script(files[current_file_index])

try:
    while True:
        # Äá»c tráº¡ng thÃ¡i cá»§a nÃºt báº¥m
        input_state = GPIO.input(BUTTON_GPIO)

        # Náº¿u nÃºt Ä‘Æ°á»£c nháº¥n (tráº¡ng thÃ¡i LOW)
        if input_state == GPIO.LOW:
            print("NÃºt báº¥m Ä‘Æ°á»£c nháº¥n, chuyá»ƒn Ä‘á»•i script")
            switch_script()

            # Äá»£i cho Ä‘áº¿n khi nÃºt Ä‘Æ°á»£c nháº£ ra trÆ°á»›c khi tiáº¿p tá»¥c vÃ²ng láº·p
            while GPIO.input(BUTTON_GPIO) == GPIO.LOW:
                time.sleep(0.1)  # Chá» má»™t chÃºt Ä‘á»ƒ trÃ¡nh láº·p láº¡i quÃ¡ nhanh

        time.sleep(0.1)  # Äá»£i má»™t chÃºt Ä‘á»ƒ trÃ¡nh xá»­ lÃ½ quÃ¡ nhanh
except KeyboardInterrupt:
    print("ChÆ°Æ¡ng trÃ¬nh bá»‹ dá»«ng")
finally:
    # Dá»n dáº¹p GPIO khi chÆ°Æ¡ng trÃ¬nh káº¿t thÃºc
    GPIO.cleanup()
    # Dá»«ng script hiá»‡n táº¡i náº¿u Ä‘ang cháº¡y
    stop_current_script()
