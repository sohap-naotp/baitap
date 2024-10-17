import serial
import requests
import RPi.GPIO as GPIO
import time

# Cáº¥u hÃ¬nh UART cho GPS
ser = serial.Serial("/dev/ttyS0", baudrate=9600, timeout=1)

# Token vÃ  Chat ID cho Telegram Bot
bot_token = '7024978108:AAGEU__LbI6z4H1W400n29ZizHygrxalc48'
chat_id = '-4556688626'

# Cáº¥u hÃ¬nh nÃºt nháº¥n
button_pin = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def convert_to_degrees(raw_value, direction):
    degrees = float(raw_value[:2])
    minutes = float(raw_value[2:]) / 60
    decimal_degrees = degrees + minutes
    if direction == 'S' or direction == 'W':  # Náº¿u tá»a Ä‘á»™ lÃ  Nam hoáº·c TÃ¢y
        decimal_degrees = -decimal_degrees
    return decimal_degrees

def read_gps_data():
    while True:
        data = ser.readline().decode('utf-8', errors='replace')  # Äá»c dá»¯ liá»‡u tá»« GPS
        if data.startswith('$GNGGA'):  # Chá»‰ láº¥y dá»¯ liá»‡u tá»« chuá»—i NMEA GNGGA
            parts = data.split(',')
            # Kiá»ƒm tra xem cÃ¡c pháº§n tá»a Ä‘á»™ khÃ´ng bá»‹ rá»—ng
            if parts[2] and parts[3] and parts[4] and parts[5]:
                lat_raw = parts[2]
                lat_dir = parts[3]
                lon_raw = parts[4]
                lon_dir = parts[5]
                lat = convert_to_degrees(lat_raw, lat_dir)
                lon = convert_to_degrees(lon_raw, lon_dir)
                return lat, lon
            else:
                print("Dá»¯ liá»‡u GPS khÃ´ng há»£p lá»‡, Ä‘á»£i tÃ­n hiá»‡u GPS...")

def send_telegram_location(lat, lon):
    """Gá»­i vá»‹ trÃ­ GPS lÃªn Telegram"""
    url = f"https://api.telegram.org/bot{bot_token}/sendLocation"
    payload = {
        'chat_id': chat_id,
        'latitude': lat,
        'longitude': lon
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("ÄÃ£ gá»­i vá»‹ trÃ­ GPS thÃ nh cÃ´ng")
        else:
            print(f"Lá»—i khi gá»­i vá»‹ trÃ­: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Lá»—i káº¿t ná»‘i: {e}")

if __name__ == "__main__":
    try:
        while True:
            if GPIO.input(button_pin) == GPIO.LOW:  # NÃºt nháº¥n Ä‘Æ°á»£c báº¥m (má»©c logic tháº¥p)
                lat, lon = read_gps_data()  # Äá»c dá»¯ liá»‡u GPS
                if lat and lon:  # Kiá»ƒm tra xem dá»¯ liá»‡u khÃ´ng pháº£i None
                    send_telegram_location(lat, lon)  # Gá»­i vá»‹ trÃ­ lÃªn Telegram vá»›i báº£n Ä‘á»“
                    print(f"ÄÃ£ gá»­i tá»a Ä‘á»™: Latitude {lat}, Longitude {lon} lÃªn Telegram vá»›i báº£n Ä‘á»“")
                time.sleep(1)  # TrÃ¡nh gá»­i nhiá»u láº§n khi nháº¥n giá»¯ nÃºt
    except KeyboardInterrupt:
        GPIO.cleanup()  # Dá»n dáº¹p cÃ¡c chÃ¢n GPIO sau khi thoÃ¡t
        print("Dá»«ng chÆ°Æ¡ng trÃ¬nh")
