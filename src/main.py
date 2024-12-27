# ----- Import -----
import bme680
from time import sleep
from os import getenv
from sys import stderr
import paho.mqtt.client as mqtt
from json import dumps

# ----- Load configuration from environment variables -----
I2C_ADDR_PRIMARY = int(getenv("I2C_PRIMARY", 0x76))
I2C_ADDR_SECONDARY = int(getenv("I2C_SECONDARY", 0x76))
POLL_TIME = int(getenv("POLL_TIME", 60))
MQTT_PORT = int(getenv("MQTT_PORT", 1883))
MQTT_ADDR = str(getenv("MQTT_ADDR", "127.0.0.1"))
MQTT_TOPIC = str(getenv("MQTT_TOPIC", "bme680"))
DISCOVERY_PREFIX = str(getenv("DISCOVERY_PREFIX", "homeassistant"))
DISCOVERY_DEVICE_ID = str(getenv("DISCOVERY_DEVICE_ID", "bme680"))

print("===================================================")
print("|==============     BME680-MQTT     ==============|")
print("|====  github.com/lillian-alicia/bme680-mqtt  ====|")
print("===================================================")

# ----- Subprograms -----

def readData(sensor:bme680.BME680) -> str:
    sensor.get_sensor_data() # Pulls new data from the sensor
    return  dumps({
                "temperature"   :       {
                    "celcius"       :       "{0:.2f}".format(sensor.data.temperature), # Temp in celcius, rounded to 2 places
                    "fahrenheit"    :       "{0:.2f}".format((sensor.data.temperature * 9/5)+32), # Temp in farenheit, rounded to 2 places
                    "raw"           :       sensor.data.temperature }, # Raw temperature value
                "pressure"          :       {
                    "pressure"      :       "{0:.3f}".format(sensor.data.pressure), # Pressure, rounded to 3 places
                    "raw"           :       sensor.data.pressure },# Raw pressure value
                "humidity"          :       {
                    "humidity"      :       "{0:.2f}".format(sensor.data.humidity), # Humidity, rounded to 2 places
                    "raw"           :       sensor.data.humidity}, # Raw humidity value
                "airQuality"        :       {
                    "resistance"    :       sensor.data.gas_resistance}
            })

def sendDiscoveryMessage(client:mqtt.Client) -> None:
    discoveryMessage = {
        "device"        :       {
            "name"      :       DISCOVERY_DEVICE_ID.upper(),
            "mf"        :       "Bosch",
            "mdl"       :       "BME680",
            "ids"       :       f"BME680_{DISCOVERY_DEVICE_ID}"
        },
        "origin"        :       {
            "name"      :       "bme680-mqtt",
            "url"       :       "https://github.com/lillian-alicia/bme680-mqtt",
            "sw"        :       "1.0"
        },
        "components"    :       {
            "temperature_celcius":      {
                "name"          :   "Temperature °C",
                "platform"      :   "sensor",
                "device_class"  :   "temperature",
                "unit_of_measurement" : "°C",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.temperature.celcius }}",
                "unique_id"     :   f"{DISCOVERY_DEVICE_ID}_temperature_celcius"
            },
            "temperature_farenheit":      {
                "name"          :   "Temperature °F",
                "platform"      :   "sensor",
                "device_class"  :   "temperature",
                "unit_of_measurement" : "°F",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.temperature.fahrenheit }}",
                "unique_id"     :   f"{DISCOVERY_DEVICE_ID}_temperature_fahrenheit"
            },
            "pressure"          :      {
                "name"          :   "Pressure",
                "platform"      :   "sensor",
                "device_class"  :   "pressure",
                "unit_of_measurement" : "hPa",
                "suggested_display_precision" : 1,
                "value_template":   "{{ value_json.pressure.pressure }}",
                "unique_id"     :   f"{DISCOVERY_DEVICE_ID}_pressure"
            },
            "humidity"          :      {
                "name"          :   "Humidity",
                "platform"      :   "sensor",
                "device_class"  :   "humidity",
                "unit_of_measurement" : "%",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.humidity.humidity }}",
                "unique_id"     :   f"{DISCOVERY_DEVICE_ID}_humidity"
            },
            "air_quality"       :       {
                "name"          :   "Air Quality",
                "platform"      :   "sensor",
                "device_class"  :   "aqi",
                "unit_of_measurement" : None,
                "suggested_display_precision" : 0,
                "value_template":   "{{ value_json.airQuality.resistance }}",
                "unique_id"     :   f"{DISCOVERY_DEVICE_ID}_air_quality"
            }},
        "state_topic"   :       MQTT_TOPIC
    }

    client.publish(topic=f"{DISCOVERY_PREFIX}/device/{DISCOVERY_DEVICE_ID}/config", payload=dumps(discoveryMessage), retain=True)

client = mqtt.Client()

try:
    sensor = bme680.BME680(I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(I2C_ADDR_SECONDARY)

try:
    client.connect(MQTT_ADDR, MQTT_PORT)
except Exception as error:
    print(f"Failed to connect to the MQTT server at {MQTT_ADDR}:{MQTT_PORT}.", file=stderr)
    print(error)

# Sensor configuration from pimoroni's examples:
# https://github.com/pimoroni/bme680-python

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

sendDiscoveryMessage(client)

while True:
    mqttData = readData(sensor)
    client.publish(topic=MQTT_TOPIC, payload=mqttData)
    sleep(POLL_TIME)