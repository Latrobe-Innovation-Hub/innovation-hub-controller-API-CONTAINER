import aiohttp
import asyncio
import logging
import time

from epson_projector.main import Projector  # Import your Projector class from main.py

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

host_address = "192.168.128.18"

# Define constants for power states
POWER_ON = "01"
POWER_INIT = "02"
POWER_OFF = "04"
POWER_ERR = "ERR"

async def test_projector_control():
    turn_off = None
    turn_on = None

    async with aiohttp.ClientSession() as session:
        host = host_address
        websession = session
        projector = Projector(host, websession)

        # Get the current power state
        power_state = await projector.get_property("PWR")
        print(f"Getting power state for projector at: {host}")
        #print(power_state)
        
        if power_state == POWER_ERR:
            # Retry initialization if the response is "ERR"
            max_retries = 15
            for retry in range(1, max_retries + 1):
                print(f"Initialization failed. Retrying attempt {retry}/{max_retries}...")
                
                # Wait before retrying (you can adjust the duration)
                #time.sleep(5)
                await asyncio.sleep(5)
                
                # Retry initialization
                power_state = await projector.get_property("PWR")
                if str(power_state) != error:
                    print("Initialization succeeded after retry.")
                    break
            else:
                print("Initialization failed after all retries. Exiting with an error statement.")
                return
        
        #if power_state == POWER_ON or power_state == POWER_INIT:
        if power_state in (POWER_ON, POWER_INIT):
            if power_state == POWER_ON:
                print(f"Projector at: {host} is on.")
            elif power_state == POWER_INIT:
                print(f"Projector at: {host} is init.")
                while power_state == POWER_INIT:
                    #time.sleep(3)
                    await asyncio.sleep(5)
                    power_state = await projector.get_property("PWR")
                    print(f"Getting power state for projector at: {host}")
                    print("power state init:", power_state)
            
            print(f"Projector at: {host} is on, so turning off..")
            turn_off = await projector.send_command("PWR OFF")
            #print(turn_off)
        elif power_state == POWER_OFF:
            print(f"Projector at: {host} is off, so turning on..")
            turn_on = await projector.send_command("PWR ON")
            #print(turn_on)
            
       
        power_state = await projector.get_property("PWR")
        
        #print("DEBUG, turn_on: ", turn_on)
        #print("DEBUG, turn_off: ", turn_off)
        
        if turn_on:
            while power_state != POWER_ON:
                # we want to confirm that power_state has changed to "01"
                
                # Wait before retrying (you can adjust the duration)
                #time.sleep(5)
                await asyncio.sleep(5)
                
                # Get the current power state
                power_state = await projector.get_property("PWR")
                
            #print(power_state)
            print(f"Projector at: {host} is confirmed on!")
                
        elif turn_off:
            while power_state != POWER_OFF:
                # we want to confirm that power_state has changed to "04"
                
                # Wait before retrying (you can adjust the duration)
                #time.sleep(5)
                await asyncio.sleep(5)
                
                # Get the current power state
                power_state = await projector.get_property("PWR")
                
            #print(power_state)
            print(f"Projector at: {host} is confirmed off!")

asyncio.get_event_loop().run_until_complete(test_projector_control())