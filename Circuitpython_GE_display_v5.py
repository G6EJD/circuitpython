# Adafruit Huzzah consumes 156uA in deep sleep mode
# Consumes
import os
print(os.uname().version) #e.g.'8.1.0 on 2023-05-28'

import gc
import time, rtc, adafruit_ntp, alarm
import ssl
import json
import wifi
import socketpool
import board
import displayio, busio
import terminalio
import adafruit_requests
import adafruit_il0373
from   adafruit_display_text import label
from   adafruit_display_shapes.rect import Rect

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

sleep_time = 600 # seconds
time_str = ""

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

GE_STATUS    = "https://api.givenergy.cloud/v1/inverter/" + secrets["InverterSerial"] + "/system-data/latest"
GE_METER     = 'https://api.givenergy.cloud/v1/inverter/CE2029G093/meter-data/latest'
Time_Address = 'https://worldtimeapi.org/api/timezone/'
Timezone     = "Europe/London"
  
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
      time.sleep(1)
      print("Connected")
      gc.collect()
      
def get_time():
  global Time_Address, Timezone, time_str
  Time_url     = Time_Address + Timezone
  print(f"Getting time from : {Time_url}")
  response = requests.get(Time_url)
  time_json = response.json()
  #print(time_json)
  #{'timezone': 'Europe/London', 'utc_datetime': '2023-05-29T18:10:53.453748+00:00',
  #'raw_offset': 0, 'client_ip': '51.198.204.217',
  #'dst_from': '2023-03-26T01:00:00+00:00',
  #'unixtime': 1685383853, 'utc_offset': '+01:00',
  #'datetime': '2023-05-29T19:10:53.453748+01:00',
  #'week_number': 22, 'abbreviation': 'BST',
  #'day_of_year': 149, 'day_of_week': 1, 'dst': True, 'dst_offset': 3600, 'dst_until': '2023-10-29T01:00:00+00:00'}
  unixtime   = time_json["unixtime"]
  dst_offset = time_json["dst_offset"]
  location_time = unixtime + dst_offset
  current_time = time.localtime(location_time)
  #print(f"Current time: {current_time}")
  time_str = f"{current_time.tm_mday:02d}/{current_time.tm_mon:02d}/{current_time.tm_year:02d} {current_time.tm_hour:02d}:{current_time.tm_min:02d}"

wifi_connect()
socket = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(socket, ssl.create_default_context())

get_time()
print(time_str)

print("\nAttempting to obtain GivEnergy stats!")  # --------------------------------
try:
    print ("Making connection request for Battery System Data...")
    response = requests.get(url=GE_STATUS, headers=GE_headers, json=payload, timeout=5)
    # Print Request 
    print("API URL: ", GE_STATUS)
    print("===============================")    #print (response.status_code, response.reason, response.headers)
    #print (response.json())
    parsed_system_data = response.json()
    GE_METER = 'https://api.givenergy.cloud/v1/inverter/CE2029G093/meter-data/latest'
    print ("Making connection request for Meter Data...")
    response = requests.get(url=GE_METER, headers=GE_headers, json=payload)
    # Print Request 
    print("API URL: ", GE_METER)
    print("===============================")
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
    #{'data': {'time': '2023-05-28T10:16:27Z',
    #'battery': {'temperature': 21, 'percent': 100, 'power': 0},
    #'solar': {'power': 2975,
    #'arrays': [{'array': 1, 'current': 12.2, 'power': 2975, 'voltage': 242},
    #{'array': 2, 'current': 0, 'power': 0, 'voltage': 0}]},
    #'grid': {'current': 0, 'frequency': 50.04, 'power': 2577, 'voltage': 244.9},
    #'inverter': {'output_voltage': 243.5, 'power': 0, 'output_frequency': 50.03, 'eps_power': 0, 'temperature': 40.3},
    #'consumption': 398}}
    StateOfCharge    = data['data']['battery']['percent']
    BatteryRemaining = "{:.1f}".format(StateOfCharge / 100 * 8.0)  # 0.768 was a measured value
    GenerationToday  = "{:.1f}".format(data['data']['solar']['power']/ 1000)
    ConsumptionToday = str("{:.1f}".format(data['data']['consumption'] / 1000))
    print ("Consumption Today       = ", ConsumptionToday, "kWh")
    print ("Battery Remaining       = ", BatteryRemaining, "kWh")
    print ("Generation Today        = ", GenerationToday, "kWh")
    print ("State of Charge         = ", StateOfCharge, "%")
            
    data = parsed_meter_data
    #print(data)
    #{'data': {'time': '2023-05-28T10:05:29Z',
    #'today': {'battery': {'discharge': 1.9, 'charge': 4.8},
    #'grid': {'import': 0, 'export': 0.1},#
    #'solar': 6.6, 'consumption': 6.5},
    #'total': {'battery': {'discharge': 3827.8, 'charge': 3827.8},
    #          'grid': {'import': 4572.6, 'export': 1724.5},
    #          'solar': 9324.6, 'consumption': 11448.3}}}
    BatteryDischargeToday  = data['data']['today']['battery']['discharge']
    BatteryChargeToday     = data['data']['today']['battery']['charge']
    BatteryThroughputToday = BatteryDischargeToday + BatteryChargeToday
        
    GridExportToday        = data['data']['today']['grid']['export']
    GridImportToday        = data['data']['today']['grid']['import']
    #str("{:.1f}".format(data['data']['today']['grid']['import']
    
    SolarProductionToday   = data['data']['today']['solar']
    SolarConsumptionToday  = data['data']['today']['consumption']
    
    print("Battery Discharge Today = ", BatteryDischargeToday, "kWh")
    print("Battery Charge Today    = ", BatteryChargeToday, "kWh")
    print("Battery Throughput      = ", BatteryThroughputToday, "kWh")
    print("Grid Export Today       = ", GridExportToday, "kWh")
    print("Grid Import Today       = ", GridImportToday, "kWh")
    print("Solar Production Today  = ", SolarProductionToday, "kWh")
    print("Solar Consumption Today = ", SolarConsumptionToday, "kWh")
    print("===============================")
    print("\nFinished!")
    print("Next Update in %s %s" % (int(sleep_int), sleep_time_conversion))
    gc.collect() # Run a garbage collection

#---
tile_grid  = displayio.Group()
palette    = displayio.Palette(1)
palette[0] = BACKGROUND_COLOR
font       = terminalio.FONT

t = displayio.TileGrid(background_bitmap, pixel_shader=palette)
tile_grid.append(t)

soc_background_rect = Rect(193, 2, 101, 61, fill=WHITE, outline=0x0, stroke=0)
tile_grid.append(soc_background_rect)

tput_background_rect = Rect(193, 65, 101, 61, fill=WHITE, outline=0x0, stroke=0)
tile_grid.append(tput_background_rect)

soc_text_group = create_text_group(16, 10, font, "SoC:" + str(StateOfCharge) + "%", 2, BLACK)
tile_grid.append(soc_text_group)

BatteryRemaining = create_text_group(67, 25, font, str(BatteryRemaining) + "kWh Remaining", 1, WHITE)
tile_grid.append(BatteryRemaining)

battput_text_group = create_text_group(135, 10, font, "TPut:" + str(BatteryThroughputToday) + "kWh", 2, BLACK)
tile_grid.append(battput_text_group)

solarproductiontoday = create_text_group(10, 40, font, "Solar Production = " + str(SolarProductionToday) + "kWh", 1, BLACK)
tile_grid.append(solarproductiontoday)

solarconsumptiontoday = create_text_group(5, 52, font, "Solar Consumption = " + str(SolarConsumptionToday) + "kWh", 1, BLACK)
tile_grid.append(solarconsumptiontoday)

chargetoday_text_group = create_text_group(35, 64, font, "Charge Today = " + str(BatteryChargeToday) + "kWh", 1, BLACK)
tile_grid.append(chargetoday_text_group)

dischargetoday_text_group = create_text_group(17, 74, font, "Discharge Today = " + str(BatteryDischargeToday) + "kWh", 1, BLACK)
tile_grid.append(dischargetoday_text_group)

exporttoday_text_group = create_text_group(35, 86, font, "Export Today = " + str(GridExportToday) + "kWh", 1, BLACK)
tile_grid.append(exporttoday_text_group)

importtoday_text_group = create_text_group(35, 98, font, "Import Today = " + str("{:.1f}".format(GridImportToday)) + "kWh", 1, BLACK)
tile_grid.append(importtoday_text_group)

# Draw Battery outline
bat_outline = Rect(220, 40, 44, 84, fill=WHITE, outline=BLACK, stroke=2)
tile_grid.append(bat_outline)
cap_outline = Rect(232, 35, 15, 5, fill=BLACK, outline=BLACK, stroke=2)
tile_grid.append(cap_outline)

# Fill battery to show charge
BatteryHeight = 80 - 2 - 2 # less top and bottom
BatteryWidth  = 40 - 2 - 2 # less left and right
BatteryCharge = int(BatteryHeight * StateOfCharge / 100)
if (BatteryCharge == 0):
    BatteryCharge = 1
bat_charge = Rect(224, 44 + BatteryHeight - BatteryCharge, BatteryWidth, BatteryCharge, fill=BLACK, outline=0, stroke=0)
tile_grid.append(bat_charge)

time_group = create_text_group(20, 120, font, "Updated: " + time_str, 1, BLACK)
tile_grid.append(time_group)

# Display the formed display
display.show(tile_grid)
display.refresh()
print("Finished...")

# Create an alarm that will trigger N-secs from now.
time_alarm = alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_time)
# Exit the program, and then deep sleep until the alarm wakes
alarm.exit_and_deep_sleep_until_alarms(time_alarm)
# Does not return, we never get here