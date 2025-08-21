from bleak import BleakClient, BleakScanner
from bleak.exc import BleakDeviceNotFoundError
import logging
import sys
import struct
from logging.handlers import RotatingFileHandler
import requests
import time
import json
import socket
import asyncio
from concurrent.futures import ThreadPoolExecutor
CONFIG_FILE="gym_collect.json"
try:
    with open(CONFIG_FILE) as cfg:
        config = json.load(cfg)
except json.decoder.JSONDecodeError as e:
    print(f"Failed to read config file {CONFIG_FILE}: {e}")
    sys.exit(1)


# Logging setup
logger = logging.getLogger("my_logger")
logger.setLevel(logging.getLevelName(config.get("log_level", "INFO")))

file_handler = RotatingFileHandler("scan.log", maxBytes=500_000, backupCount=3)
formatter = logging.Formatter("%(asctime)s %(levelname)s:%(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter("%(levelname)s:%(message)s"))
console_handler.setLevel(logging.INFO)

logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.info("Program Started")

# UUIDs
CYCLING_POWER_MEASUREMENT_UUID = "00002a63-0000-1000-8000-00805f9b34fb"
HRM_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
BATTERY_LEVEL_UUID = "00002a19-0000-1000-8000-00805f9b34fb"

# Crank tracking
previous_crank_revs = None
previous_crank_event_time = None

# constants used for sending old-skool events to Splunk Enterprise, as a backup for the OTel route

# Permanent instance for developing

# Instance  set up for .conf
#EVENTS_HEC_URL = "https://3.81.86.55:8088/services/collector/event"
#EVENTS_HEC_HEADERS = {'Authorization': 'Splunk 74388eea-1a58-42d7-bae7-be8796400892','Content-Type': 'application/json'}

HOSTNAME=socket.gethostname()

# constants for OTel
MAX_WORKERS=5
#O11y_endpoint="https://ingest.eu2.signalfx.com/v2/datapoint"
#O11y_token="gy3QkXtKG06UOI4rx4eG7g"
session = requests.Session()

def decode_power_data(data: bytearray):
    global previous_crank_revs, previous_crank_event_time

    flags, instantaneous_power = struct.unpack_from("<HH", data, 0)
    offset = 4

    result = {
        "flags": flags,
        "power_watts": instantaneous_power
    }

    has_crank_revs = flags & (1 << 5)

    if has_crank_revs:
        cumulative_crank_revs, last_crank_event_time = struct.unpack_from("<HH", data, offset)
        max_uint16 = 65536

        if previous_crank_revs is not None and previous_crank_event_time is not None:
            # discard every other reading (half turn of cranks) where there is no rpm
            # and also (in testing) the power value is same as previous reading
            if (cumulative_crank_revs == previous_crank_revs):
                return {}
            delta_revs = (cumulative_crank_revs - previous_crank_revs) % max_uint16
            delta_time = ((last_crank_event_time - previous_crank_event_time) % max_uint16) / 1024.0
            rpm = int((delta_revs / delta_time) * 60) if delta_time > 0 else 0
            logger.debug(f"cumm_revs={cumulative_crank_revs} prev={previous_crank_revs} rpm={rpm} delta={delta_time}")
            result["rpm"] = rpm
            if rpm>config["MAX_RPM_IGNORE"]:
                logger.info(f"ignoring high RPM calc: {rpm}")
                return {}
        else:
            rpm = None
            result = {}

        previous_crank_revs = cumulative_crank_revs
        previous_crank_event_time = last_crank_event_time

    logger.debug(f"decode finished: power={instantaneous_power} rpm={rpm} result={str(result)} len={len(result)}")
    return result

def send_otel_request(payload):
    try:
        response = session.post(
            f'{config["O11Y_ENDPOINT"]}',
            headers={"X-SF-TOKEN": config["O11Y_TOKEN"], "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code != 200:
            logger.error(f"Error {response.status_code}: {response.text}")
            logger.error(f"Payload: {json.dumps(payload, indent=2)}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error: {e}")
    

async def connect_to_power_meter(address):
  logger.info("Looking for specific Power Meter with address: %s", address)

  while True:
    # Wait for specific address to be available
    retries = 0
    while True:
        devices = await BleakScanner.discover()
        found = any(d.address == address or d.name == address for d in devices)
        if found:
            break
        retries += 1
        if retries % 12 == 0:
            logger.info("waiting to connect to bluetooth device with address %s",address)
        await asyncio.sleep(5)


    try:
        async with BleakClient(address) as client:
            logger.info("Connected to power meter")

            async def handle_power_notification(sender, data):
                logger.debug(f"Raw BLE Data (bytes) {list(data)}")
                decoded = decode_power_data(data)
                if not decoded:
                    return
                power_watts = decoded['power_watts']
                if "rpm" in decoded:
                    rpm = decoded['rpm']
                    if rpm==0:
                        return
                    logger.info("pedal_power_watts=%s rpm=%s", power_watts, rpm)
                    # Send an old-skool event to the Splunk Cloud event HEC
                    try:
                        hec_payload = json.dumps({"time": int(time.time()),
                                   "host": HOSTNAME,
                                   "source":__file__,
                                   "event": {
                                       "metric":"cycle_power",
                                       "cycle_power_watts": power_watts,
                                       "cycle_rpm":rpm,
                                       "device_address":address
                                       }
                                  })
                        logger.debug("HEC power payload: %s", hec_payload)
                        requests.post(config["EVENTS_HEC_URL"], data=hec_payload, headers=config["EVENTS_HEC_HEADERS"])
                    except Exception as e:
                        logger.warning(f"Failed to send power data to HEC: {e}")
                    
                    # Send Otel data straight to O11y cloud endpoint using python libs
                    otel_payload = {'gauge':[{"metric":"pedal_power_watts",
                                         "value": f"{power_watts}",
                                         "dimensions": {"device_address": f"{address}","host":f"{HOSTNAME}"}},
                                         {"metric":"pedal_power_rpm",
                                         "value": f"{rpm}",
                                         "dimensions": {"device_address": f"{address}","host":f"{HOSTNAME}"}}]}
                    logger.debug("OTel pedal power payload: %s", otel_payload)

                    # Use a thread pool for concurrent execution
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        executor.submit(send_otel_request, otel_payload)

                else:
                    # should never get here. In theory the RPM field is optional but for our pedals should always be there
                    logger.info("pedal_power_watts=%s", decoded['power_watts'])


            await client.start_notify(CYCLING_POWER_MEASUREMENT_UUID, handle_power_notification)

            # Now we continue to loop forever so long as there is battery data
            # when that finishes we assume disconnection
            # So the battery check is also the connection check
            while True:
                try:
                    battery_data = await client.read_gatt_char(BATTERY_LEVEL_UUID)
                    battery_level = int(battery_data[0])
                    logger.info(f"pedal_battery_pct={battery_level}")

                    # Send an old-skool event to the Splunk Cloud event HEC
                    try:
                        hec_payload = json.dumps({"time": int(time.time()),
                                   "host": HOSTNAME,
                                   "source":__file__,
                                   "event": {
                                       "metric":"cycle_power_battery",
                                       "cycle_power_battery_pct":battery_level,
                                       "device_address":address
                                       }
                                  })
                        logger.debug("HEC power battery payload: %s", hec_payload)
                        requests.post(config["EVENTS_HEC_URL"], data=hec_payload, headers=config["EVENTS_HEC_HEADERS"])
                    except Exception as e:
                        logger.warning(f"Failed to send power meter battery to HEC: {e}")

                    # Send Otel data straight to O11y cloud endpoint using python libs
                    otel_payload = {'gauge':[{"metric":"power_meter_battery",
                                         "value": f"{battery_level}",
                                         "dimensions": {"device_address": f"{address}","host":f"{HOSTNAME}"}}]}
                    logger.debug("OTel power meter battery payload: %s", otel_payload)

                    # Use a thread pool for concurrent execution
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        executor.submit(send_otel_request, otel_payload)

                except Exception as e:
                    logger.warning(f"Failed to read pedal battery, assuming device disconnected: {e}")
                    break
                await asyncio.sleep(60)

            try:
                await client.stop_notify(CYCLING_POWER_MEASUREMENT_UUID)
            except Exception as e:
                logger.warning(f"Pedals stop_notify call failed: {e}")

    except BleakDeviceNotFoundError as e:
        logger.error(f"BleakDeviceNotFoundError: {e}")


async def connect_to_hrm(address):
  logger.info("Looking for specific HRM with address: %s", address)
  while True:
    # Wait for specific HRMaddress to be available
    retries = 0
    while True:
        devices = await BleakScanner.discover()
        found = any(d.address == address or d.name == address for d in devices)
        if found:
            break
        retries += 1
        if retries % 12 == 0:
            logger.info("waiting to connect to HRM device with address %s",address)
        await asyncio.sleep(5)

    try:
        async with BleakClient(address) as client:
            logger.info(f"Connected to HRM at {address}")

            def handle_heart_rate(_, data):
                heart_rate = data[1] if data[0] & 0x01 == 0 else struct.unpack_from("<H", data, 1)[0]
                logger.info(f"Heart Rate: {heart_rate} bpm")
                # Send an old-skool event to the Splunk Cloud event HEC
                try:
                    hec_payload = json.dumps({"time": int(time.time()),
                               "host":HOSTNAME,
                               "source":__file__,
                               "event": {
                                   "metric":"heart_rate",
                                   "heart_rate":heart_rate,
                                   "device_address":address
                                   }
                              })
                    logger.debug("HEC HRM payload: %s", hec_payload)
                    requests.post(config["EVENTS_HEC_URL"], data=hec_payload, headers=config["EVENTS_HEC_HEADERS"])
                except Exception as e:
                    logger.warning(f"Failed to send HRM data to HEC: {e}")

                # Send Otel data straight to O11y cloud endpoint using python libs
                # reduces latency risk vs going via an OTel collector
                #  - but real reason is I couldn't get OTel collector to work!!
                otel_payload = {'gauge':[{"metric":"heart_rate",
                                     "value": heart_rate,
                                     "dimensions": {"device_address": f"{address}","host":f"{HOSTNAME}"}
                                    }]}
                logger.debug("OTel HRM payload: %s", otel_payload)

                # Use a thread pool for concurrent execution
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    executor.submit(send_otel_request, otel_payload)



            await client.start_notify(HRM_CHAR_UUID, handle_heart_rate)

            # Now we continue to loop forever so long as there is battery data
            # when that finishes we assume disconnection
            # So the battery check is also the connection check
            while True:
                try:
                    battery_data = await client.read_gatt_char(BATTERY_LEVEL_UUID)
                    battery_level = int(battery_data[0])
                    logger.info(f"hrm_battery_pct={battery_level}")

                    # Send an old-skool event to the Splunk Cloud event HEC
                    try:
                        hec_payload = json.dumps({"time": int(time.time()),
                                   "host": HOSTNAME,
                                   "source":__file__,
                                   "event": {
                                       "metric":"hrm_battery",
                                       "hrm_battery_pct":battery_level,
                                       "device_address":address
                                       }
                                  })
                        logger.debug("HEC hrm battery payload: %s", hec_payload)
                        requests.post(config["EVENTS_HEC_URL"], data=hec_payload, headers=config["EVENTS_HEC_HEADERS"])
                    except Exception as e:
                        logger.warning(f"Failed to send hrm battery to HEC: {e}")

                    # Send Otel data straight to O11y cloud endpoint using python libs
                    otel_payload = {'gauge':[{"metric":"hrm_battery",
                                         "value": f"{battery_level}",
                                         "dimensions": {"device_address": f"{address}","host":f"{HOSTNAME}"}}]}
                    logger.debug("OTel HRM battery payload: %s", otel_payload)

                    # Use a thread pool for concurrent execution
                    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                        executor.submit(send_otel_request, otel_payload)

                except Exception as e:
                    logger.warning(f"Failed to read HRM battery - assuming device disconnected: {e}")
                    break
                await asyncio.sleep(60)

            try:
                await client.stop_notify(BATTERY_LEVEL_UUID)
            except Exception as e:
                logger.warning(f"HRM stop_notify call failed: {e}")

    except Exception as e:
        logger.error(f"HRM connection failed: {e}")

async def main():
    # List all the Bluetooth Devices available
    logger.info("Scanning for BLE devices...")
    devices = await BleakScanner.discover()
    for d in devices:
        logger.info(f"Found: {d.name} - {d.address}")

    # Launch all connections
    await asyncio.gather(
        *[connect_to_power_meter(address) for address in config["PM_ADDRESSES"]],
        *[connect_to_hrm(address) for address in config["HRM_ADDRESSES"]]
    )

if __name__ == "__main__":
    asyncio.run(main())

