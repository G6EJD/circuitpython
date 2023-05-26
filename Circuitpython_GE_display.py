import gc
import time
import ssl
import json
import wifi
import socketpool
import adafruit_requests
import busio
import board
import displayio
import terminalio
import adafruit_il0373
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect

WIDTH  = 296
HEIGHT = 128

BLACK     = 0x000000
DARKGREY  = 0x666666
LIGHTGREY = 0x999999
WHITE     = 0xFFFFFF

FOREGROUND_COLOR = BLACK
BACKGROUND_COLOR = WHITE

VERDANA_BOLD = "/fonts/Verdana-Bold-18.bdf"

def create_text_group(x, y, font, text, scale, colour):
    text_group = displayio.Group(scale=scale, x=x, y=y)
    text_area = label.Label(font, text=text, color=colour)
    text_group.append(text_area)
    return text_group

displayio.release_displays()

spi = busio.SPI(board.IO5, board.IO18)  # Uses SCK and MOSI
epd_cs = board.IO15
epd_dc = board.IO33

display_bus = displayio.FourWire(spi, command=epd_dc, chip_select=epd_cs, baudrate=1000000)
time.sleep(1)

display = adafruit_il0373.IL0373(
    display_bus,
    width=WIDTH,
    height=HEIGHT,
    rotation=270,
    black_bits_inverted=False,
    color_bits_inverted=False,
    grayscale=True,
    refresh_time=1,
)

background_bitmap = displayio.Bitmap(WIDTH, HEIGHT, 1)

try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

# Github developer token required.
# Ensure these are uncommented and in secrets.py or .env
# "Github_username": "Your Github Username",
# "Github_token": "Your long API token",

# Initialize WiFi Pool (There can be only 1 pool & top of script)
pool = socketpool.SocketPool(wifi.radio)

# Time between API refreshes
# 900 = 15 mins, 1800 = 30 mins, 3600 = 1 hour
sleep_time = 30

try:
    from secrets import secrets
except ImportError:
    print("Secrets File Import Error")
    raise

if sleep_time < 60:
    sleep_time_conversion = "seconds"
    sleep_int = sleep_time
elif 60 <= sleep_time < 3600:
    sleep_int = sleep_time / 60
    sleep_time_conversion = "minutes"
elif 3600 <= sleep_time < 86400:
    sleep_int = sleep_time / 60 / 60
    sleep_time_conversion = "hours"
else:
    sleep_int = sleep_time / 60 / 60 / 24
    sleep_time_conversion = "days"
    
#---    
print("Starting...");
payload = {
    "inverter_serials": [
        secrets["InverterSerial"]
    ],
    "setting_id": 17
}

GE_headers = {
  'Authorization': 'Bearer ' + secrets["API_Key"],
  'Content-Type': 'application/json',
  'Accept': 'application/json',
  'Connection': 'close'
}

GE_SOURCE  = "https://api.givenergy.cloud/v1/inverter/" + secrets["InverterSerial"] + "/system-data/latest"

def wifi_connect():
  # Connect to Wi-Fi
  print("\n===============================")
  print("Connecting to WiFi...")
  while not wifi.radio.ipv4_address:
      try:
          wifi.radio.connect(secrets["ssid"], secrets["password"])
      except ConnectionError as e:
          print("Connection Error:", e)
          print("Retrying in 10 seconds")
      time.sleep(10)
      gc.collect()
      print("Connected!")

while True:
    try:
        wifi.radio.connect(secrets["ssid"], secrets["password"])
        print("Connected to %s!"%secrets["ssid"])
        print("My IP address is", wifi.radio.ipv4_address)
    except ConnectionError as e:
        print("Connection Error:", e)
        print("Retrying in 10 seconds")
        time.sleep(10)
    print("Connected!")
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl.create_default_context())
    #wifi_connect()
    try:
        print("\nAttempting to GET GE Stats!")  # --------------------------------
        # Print Request to Serial
        debug_request = True  # Set true to see full request
        if debug_request:
            print("Full API GET URL: ", GE_SOURCE)
        print("===============================")
        try:
            print ("Making connection request for System Data...")
            response = requests.get(url=GE_SOURCE, headers=GE_headers, json=payload, timeout=5)
            #print (response.status_code, response.reason, response.headers)
            #print (response.json())
            parsed_system_data = response.json()
            url = 'https://api.givenergy.cloud/v1/inverter/CE2029G093/meter-data/latest'
            print ("Making connection request for Meter Data...")
            response = requests.get(url=url, headers=GE_headers, json=payload)
            parsed_meter_data = response.json()
            #print (response.json())
            response.close()
        except ConnectionError as e:
            print("Connection Error:", e)
            print("Retrying in 10 seconds")
            response.close()
        debug_response = True  # Set true to see full response
        if debug_response:
            data = parsed_system_data
            #print(data)
            #{'data': {'time': '2023-05-26T11:46:23Z',
            #'battery': {'temperature': 20, 'percent': 100, 'power': 0},
            #'solar': {'power': 3306,
            #'arrays': [{'array': 1, 'current': 13.3, 'power': 3306, 'voltage': 247.6},
            #{'array': 2, 'current': 0, 'power': 0, 'voltage': 0}]},
            #'grid': {'current': 0, 'frequency': 49.98, 'power': 3006, 'voltage': 250.6},
            #'inverter': {'output_voltage': 249.1, 'power': 0, 'output_frequency': 49.97, 'eps_power': 0, 'temperature': 28.1},
            #'consumption': 300}}
            stateOfCharge          = data['data']['battery']['percent']
            batteryRemaining       = "{:.1f}".format(stateOfCharge / 100 * 7.7)  # 0.768 was a measured value
            GenerationToday        = "{:.1f}".format(data['data']['solar']['power']/ 1000)
            ConsumptionToday       = str("{:.1f}".format(data['data']['consumption'] / 1000))
            print ("Consumption Today  = ", ConsumptionToday, "kWh")
            print ("Battery Remaining  = ", batteryRemaining, "kWh")
            print ("Generation Today   = ", GenerationToday, "kWh")
            print ("State of Charge    = ", stateOfCharge, "%")
            
            data = parsed_meter_data
            #print(data)
            #{'data': {'time': '2023-05-26T14:46:50Z',
            #'today': {'battery': {'discharge': 1.9, 'charge': 5},
            #'grid': {'import': 0.7, 'export': 6.5},#
            #'solar': 21.2, 'consumption': 15.4},
            #'total': {'battery': {'discharge': 3819.2, 'charge': 3819.2},
            #'grid': {'import': 4571.5, 'export': 1712.7},
            #'solar': 9288.5, 'consumption': 11424.1}}}
            ChargeToday            = str("{:.1f}".format(data['data']['today']['battery']['charge']))
            DischargeToday         = str("{:.1f}".format(data['data']['today']['battery']['discharge']))
            ExportToday            = str("{:.1f}".format(data['data']['today']['grid']['export']))
            ImportToday            = str("{:.1f}".format(data['data']['today']['grid']['import']))
            dischargeEnergyToday   = str("{:.1f}".format(data['data']['today']['battery']['discharge']))
            batteryThroughputToday = str("{:.1f}".format(data['data']['today']['battery']['charge'] + data['data']['today']['battery']['discharge']))
            print("Charge Today       = ", ChargeToday, "kWh")
            print("Discharge Today    = ", DischargeToday, "kWh")
            print("Export Today       = ", ExportToday, "kWh")
            print("Import Today       = ", ImportToday, "kWh")
            print("Battery Discharge  = ", dischargeEnergyToday, "kWh")
            print("Battery Throughput = ", batteryThroughputToday, "kWh")
            
        print("\nFinished!")
        print("Next Update in %s %s" % (int(sleep_int), sleep_time_conversion))
        print("===============================")
        gc.collect()

    except (ValueError, RuntimeError) as e:
        print("Failed to get data, retrying\n", e)
        time.sleep(60)
        continue
    #---
    tile_grid  = displayio.Group()
    palette    = displayio.Palette(1)
    palette[0] = BACKGROUND_COLOR

    t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
    tile_grid.append(t)

    background_rect = Rect(2, 2, 189, 124, fill=WHITE, outline=0x0, stroke=0)
    tile_grid.append(background_rect)

    soc_background_rect = Rect(193, 2, 101, 61, fill=WHITE, outline=0x0, stroke=0)
    tile_grid.append(soc_background_rect)

    throughput_background_rect = Rect(193, 65, 101, 61, fill=WHITE, outline=0x0, stroke=0)
    tile_grid.append(throughput_background_rect)

    soc_text_group = create_text_group(199, 30, terminalio.FONT, str(stateOfCharge) + "%", 2, BLACK)
    tile_grid.append(soc_text_group)

    batthroughput_text_group = create_text_group(199, 90, terminalio.FONT, str(batteryThroughputToday) + "kWh", 2, BLACK)
    tile_grid.append(batthroughput_text_group)

    test_text_group = create_text_group(10, 30, terminalio.FONT, "State of Charge", 2, BLACK)
    tile_grid.append(test_text_group)
    
    test2_text_group = create_text_group(10, 90, terminalio.FONT, "Bat. Throughput", 2, BLACK)
    tile_grid.append(test2_text_group)

    display.show(tile_grid)
    display.refresh()
    
    #Making connection request for System Data...
    #Failed to get data, retrying
    #Sending request failed
    gc.collect()
    #---
    time.sleep(sleep_time)