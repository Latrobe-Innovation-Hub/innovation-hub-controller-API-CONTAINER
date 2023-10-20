## ============================================================================================
## Open youtube video in chrome, make full screen and auto play.
## has flag option to loop video or not
##
## requires google chrome to be installed on host device
##
## example usage: python browser-youtube.py https://www.youtube.com/watch?v=9_S_8MspxKw --loop
## ============================================================================================



from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import os
import time
import argparse

def play_youtube_video(youtube_url, loop_is_wanted):
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

    # Wait for the page to load
    time.sleep(2)

    # Hover over the video player's controls to make the full-screen button visible
    controls = driver.find_element(By.CSS_SELECTOR, "div.ytp-chrome-controls")
    ActionChains(driver).move_to_element(controls).perform()

    # Click the full-screen button
    fullscreen_button = driver.find_element(By.CSS_SELECTOR, "button.ytp-fullscreen-button.ytp-button")
    fullscreen_button.click()

    # Wait for the video to go full-screen
    time.sleep(2)

    # Perform a right-click on the video window to open the context menu
    video_window = driver.find_element(By.CSS_SELECTOR, "video.html5-main-video")
    ActionChains(driver).context_click(video_window).perform()

    # Wait for the context menu to appear
    context_menu = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ytp-contextmenu")))

    # Find and click the "Loop" option in the context menu
    loop_option = context_menu.find_element(By.XPATH, "//div[@class='ytp-menuitem-label' and text()='Loop']")

    # Check if the "Loop" option is enabled
    loop_enabled = "ytp-menuitem-checked" in loop_option.get_attribute("class")

    if not loop_enabled and loop_is_wanted:
        loop_option.click()
    if loop_enabled and not loop_is_wanted:
        loop_option.click()

    # Close the context menu
    driver.execute_script("arguments[0].style.display = 'none';", context_menu)

    while True:
        current_time = driver.execute_script("return document.querySelector('video').currentTime")
        duration = driver.execute_script("return document.querySelector('video').duration")

        if duration is not None and current_time >= duration:
            break

        # Check for the "Skip Ad" button and click it if it's available
        #try:
        #    skip_ad_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[@class='ytp-ad-skip-button-container']//button[contains(@class, 'ytp-ad-skip-button')]")))
        #    skip_ad_button.click()
        #except:
            #pass

        time.sleep(1)  # Check every 5 seconds

    # Close the browser after the video has finished
    driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play a YouTube video with loop option")
    parser.add_argument("youtube_url", help="URL of the YouTube video to play")
    parser.add_argument("--loop", action="store_true", help="Enable loop option")

    args = parser.parse_args()

    youtube_url = args.youtube_url
    loop_is_wanted = args.loop

    play_youtube_video(youtube_url, loop_is_wanted)