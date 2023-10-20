from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time
import argparse

def toggle_captions(driver, enable_captions):
    # Locate the captions button by its class name
    captions_button = driver.find_element(By.CLASS_NAME, "ytp-subtitles-button")

    # Check if captions are currently enabled
    captions_enabled = "true" in captions_button.get_attribute("aria-pressed")

    print(f"Captions enabled: {captions_enabled}")

    # If the current state is not what is desired, click the captions button to toggle
    if captions_enabled != enable_captions:
        captions_button.click()

def play_youtube_video(youtube_url, loop_is_wanted, enable_captions):
    pid = os.getpid()
    print("PID:", pid)  # Print the PID to the console

    # Set up the Chrome driver with the --disable-infobars argument
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-fullscreen")
    chrome_options.add_argument("--disable-infobars")  # Hide the infobars message
    chrome_options.add_argument("--disable-notifications")

    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=chrome_options)

    # Open the provided YouTube URL
    driver.get(youtube_url)

    print(f"Opened URL: {youtube_url}")

    # Wait for the page to load
    time.sleep(5)  # Increase wait time to allow the page to load

    # Enable or disable captions as desired
    toggle_captions(driver, enable_captions)

    print(f"Captions toggled to: {enable_captions}")

    # Hover over the video player's controls to make the full-screen button visible
    controls = driver.find_element(By.CSS_SELECTOR, "div.ytp-chrome-controls")
    ActionChains(driver).move_to_element(controls).perform()

    # Click the full-screen button
    fullscreen_button = driver.find_element(By.CSS_SELECTOR, "button.ytp-fullscreen-button.ytp-button")
    fullscreen_button.click()

    print("Clicked full-screen button")

    # Wait for the video to go full-screen
    time.sleep(5)

    # Perform a right-click on the video window to open the context menu
    video_window = driver.find_element(By.CSS_SELECTOR, "video.html5-main-video")
    ActionChains(driver).context_click(video_window).perform()

    print("Performed right-click on video window")

    # Wait for the context menu to appear
    context_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ytp-contextmenu")))

    print("Context menu appeared")


    # Find and click the "Loop" option in the context menu
    loop_option = driver.find_element(By.CSS_SELECTOR, 'div.ytp-popup.ytp-contextmenu div.ytp-menuitem-label')
    
    loop_enabled = "ytp-menuitem-checked" in loop_option.get_attribute("class")

    print(f"Loop enabled: {loop_enabled}")

    # Define whether you want the "Loop" option to be enabled
    if loop_is_wanted != loop_enabled:
        loop_option.click()

        print(f"Clicked Loop option to {'enable' if loop_is_wanted else 'disable'}")

    # Close the context menu
    driver.execute_script("arguments[0].style.display = 'none';", context_menu)

    print("Closed context menu")

    while True:
        current_time = driver.execute_script("return document.querySelector('video').currentTime")
        duration = driver.execute_script("return document.querySelector('video').duration")

        if duration is not None and current_time >= duration:
            break

        time.sleep(1)

    print("Video finished")

    # Close the browser after the video has finished
    driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play a YouTube video with loop option and captions control")
    parser.add_argument("youtube_url", help="URL of the YouTube video to play")
    parser.add_argument("--loop", action="store_true", help="Enable loop option")
    parser.add_argument("--captions", action="store_true", help="Enable captions")

    args = parser.parse_args()

    youtube_url = args.youtube_url
    loop_is_wanted = args.loop
    enable_captions = args.captions

    play_youtube_video(youtube_url, loop_is_wanted, enable_captions)
