#!/bin/bash

install_chromedriver() {
    local chromedriver_url="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/117.0.5938.92/linux64/chromedriver-linux64.zip"

    # Download the Chromedriver ZIP file
    curl -O "$chromedriver_url"

    # Unzip the Chromedriver directly to the specified directory
    unzip -o chromedriver-linux64.zip

    # Rename the Chromedriver file if needed
    mv "chromedriver-linux64/chromedriver" "chromedriver"

    # Make the Chromedriver executable
    chmod +x "chromedriver"

    # Clean up the ZIP file and subdirectory (if created)
    rm chromedriver-linux64.zip
    rm -rf "chromedriver-linux64"

    # Display a success message
    echo "Chromedriver has been downloaded and installed to $chromedriver_dir"
}

install_chromedriver
