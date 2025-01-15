# ----- Import -----
import asyncio
import bme680
import aiomqtt as mqtt
from json import dumps
from os import getenv
from sys import stderr

# ----- Software Version (used in discovery)
SW_VERSION = "1.1.1"

# ----- Load configuration from environment variables -----
I2C_ADDR_PRIMARY = int(getenv("I2C_ADDR", 0x76))
MQTT_ADDR = str(getenv("MQTT_ADDR", "127.0.0.1"))
MQTT_PORT = int(getenv("MQTT_PORT", 1883))
MQTT_TOPIC = str(getenv("MQTT_TOPIC", "bme680"))
POLL_TIME = int(getenv("POLL_TIME", 60))
DISCOVERY_TOPIC = str(getenv("DISCOVERY_PREFIX", "homeassistant"))
DEVICE_ID = str(getenv("DISCOVERY_DEVICE_ID", "bme680"))

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
            
def discoveryMessage() -> str:
    discoveryMessage = {
        "device"        :       {
            "name"      :       DEVICE_ID.upper(),
            "mf"        :       "Bosch",
            "mdl"       :       "BME680",
            "ids"       :       f"BME680_{DEVICE_ID}"
        },
        "origin"        :       {
            "name"      :       "bme680-mqtt",
            "url"       :       "https://github.com/lillian-alicia/bme680-mqtt",
            "sw"        :       SW_VERSION
        },
        "components"    :       {
            "temperature_celcius":      {
                "name"          :   "Temperature °C",
                "platform"      :   "sensor",
                "device_class"  :   "temperature",
                "unit_of_measurement" : "°C",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.temperature.celcius }}",
                "unique_id"     :   f"{DEVICE_ID}_temperature_celcius"
            },
            "temperature_farenheit":      {
                "name"          :   "Temperature °F",
                "platform"      :   "sensor",
                "device_class"  :   "temperature",
                "unit_of_measurement" : "°F",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.temperature.fahrenheit }}",
                "unique_id"     :   f"{DEVICE_ID}_temperature_fahrenheit"
            },
            "pressure"          :      {
                "name"          :   "Pressure",
                "platform"      :   "sensor",
                "device_class"  :   "pressure",
                "unit_of_measurement" : "hPa",
                "suggested_display_precision" : 1,
                "value_template":   "{{ value_json.pressure.pressure }}",
                "unique_id"     :   f"{DEVICE_ID}_pressure"
            },
            "humidity"          :      {
                "name"          :   "Humidity",
                "platform"      :   "sensor",
                "device_class"  :   "humidity",
                "unit_of_measurement" : "%",
                "suggested_display_precision" : 2,
                "value_template":   "{{ value_json.humidity.humidity }}",
                "unique_id"     :   f"{DEVICE_ID}_humidity"
            },
            "air_quality"       :       {
                "name"          :   "Air Quality",
                "platform"      :   "sensor",
                "device_class"  :   "aqi",
                "unit_of_measurement" : None,
                "suggested_display_precision" : 0,
                "value_template":   "{{ value_json.airQuality.resistance }}",
                "unique_id"     :   f"{DEVICE_ID}_air_quality"
            }},
        "state_topic"   :       MQTT_TOPIC
    }

    return dumps(discoveryMessage)

def initSensor() -> bme680.BME680:
    try:
        sensor = bme680.BME680(I2C_ADDR_PRIMARY)
    except:
        raise OSError(f"Failed to open i2c device at address '{I2C_ADDR_PRIMARY}'. Check the I2C_ADDR_PRIMARY environment variable.")

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

    return sensor

# ----- Main -----
async def main():
    SENSOR = initSensor()
    client = mqtt.Client(hostname=MQTT_ADDR, port=MQTT_PORT)

    # ----- HomeAssistant Discovery
    try:
        async with client:
            discoveryTopic = f"{DISCOVERY_TOPIC}/device/{DEVICE_ID}/config"
            await client.publish(topic=discoveryTopic, payload=discoveryMessage(), qos=2)
    except mqtt.MqttError as exception:
        print(f"Failed to send discovery message to '{DISCOVERY_TOPIC}' at {client._hostname}:{client._port} \n{exception}", file=stderr)

    # ----- Main Loop -----
    while True:
        try:
            sensorData = readData(sensor=SENSOR)
            async with client:
                await client.publish(topic=MQTT_TOPIC, payload=sensorData, qos=2, timeout=5) # QOS 2 requests a delivery receipt, timeout will give up after 5 seconds.
        except mqtt.MqttError as exception:
            print(f"Publishing to {MQTT_TOPIC} failed, reconnecting in 30s.", file=stderr)
            print(f"More info: {exception}", file=stderr)
            await asyncio.sleep(30)
        await asyncio.sleep(POLL_TIME)
asyncio.run(main())