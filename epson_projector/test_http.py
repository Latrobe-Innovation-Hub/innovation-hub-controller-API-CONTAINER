import epson_projector as epson
from epson_projector.const import POWER, PWR_ON, PWR_OFF

import asyncio
import aiohttp
import logging
import time

_LOGGER = logging.getLogger(__name__)

console_handler = logging.StreamHandler()
console_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
_LOGGER.addHandler(console_handler)
_LOGGER.setLevel(logging.INFO)

logging.basicConfig(level=logging.INFO)

async def main_web():
    """Run main with aiohttp ClientSession."""
    async with aiohttp.ClientSession() as session:
        await run(session)

on = "01"
init = "02"
off = "04"
error = "ERR"

host = "192.168.128.18"

#"PWR ON": [("KEY", "3B")],

async def run(websession):
    """Use Projector class of epson module and check if it is turned on."""
    projector = epson.Projector(
        host=host,
        websession=websession,
        type="http"
    )
    
    power_state = await projector.get_property(POWER)
    print(f"Getting power state for projector at: {host}")
    print(power_state)
    
    if str(power_state) == error:
        # Retry initialization if the response is "ERR"
        max_retries = 15
        for retry in range(1, max_retries + 1):
            print(f"Initialization failed. Retrying attempt {retry}/{max_retries}...")
            
            # Wait before retrying (you can adjust the duration)
            time.sleep(5)
            
            # Retry initialization
            power_state = await projector.get_property(POWER)
            if str(power_state) != error:
                print("Initialization succeeded after retry.")
                break
        else:
            print("Initialization failed after all retries. Exiting with an error statement.")
            return
    
    if str(power_state) == on or str(power_state) == init:
        if str(power_state) == on:
            print(f"Projector at: {host} is on.")
        elif str(power_state) == init:
            print(f"Projector at: {host} is init.")
            while power_state == init:
                time.sleep(3)
                power_state = await projector.get_property(POWER)
                print(f"Getting power state for projector at: {host}")
                print("power state init:", power_state)
        
        print(f"Projector at: {host} is on, so turning off..")
        turn_off = await projector.send_command(PWR_OFF)
        print(turn_off)
    elif str(power_state) == off:
        print(f"Projector at: {host} is off, so turning on..")
        turn_on = await projector.send_command(PWR_ON)
        print(turn_on)

asyncio.get_event_loop().run_until_complete(main_web())
