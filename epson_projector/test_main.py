import aiohttp
import asyncio
import logging

from epson_projector.main import Projector  # Import your Projector class from main.py

_LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

async def test_projector_control():
    async with aiohttp.ClientSession() as session:
        host = "192.168.128.18"
        websession = session
        projector = Projector(host, websession)

        # Get the current power state
        power_state = await projector.get_property("PWR")
        print(f"Current Power State: {power_state}")

        # Toggle the power state
        if power_state == "01":  # If the projector is on
            print("Turning off the projector...")
            result = await projector.send_command("PWR OFF")
            print("Power off response:", result)
        elif power_state == "04":  # If the projector is off
            print("Turning on the projector...")
            result = await projector.send_command("PWR ON")
            print("Power on response:", result)
        else:
            print("Invalid power state")

asyncio.get_event_loop().run_until_complete(test_projector_control())
