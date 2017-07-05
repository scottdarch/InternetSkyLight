#!/usr/bin/env python2

# Copyright 2017 Scott A Dixon
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os
import clocks

import Adafruit_CharLCD as LCD
import Adafruit_GPIO.MCP230xx as MCP

# +----------------------------------------------------------------------------+
# | CONSTANTS
# +----------------------------------------------------------------------------+

# Define MCP pins connected to the LCD.
lcd_rs        = 1
lcd_en        = 2
lcd_d4        = 3
lcd_d5        = 4
lcd_d6        = 5
lcd_d7        = 6
lcd_backlight = 7

# Define LCD column and row size for 16x2 LCD.
lcd_columns = 16
lcd_rows    = 2

lcd_backlight_on = 0.0
lcd_backlight_off = 1.0

iprefresh_time_seconds = 5

# +----------------------------------------------------------------------------+
# | MAIN
# +----------------------------------------------------------------------------+

def main():
    # Initialize MCP23017 device using its default 0x20 I2C address.
    gpio = MCP.MCP23008(busnum=2)
    
    # Initialize the LCD using the pins
    lcd = LCD.Adafruit_CharLCD(
                            lcd_rs, 
                            lcd_en, 
                            lcd_d4, 
                            lcd_d5, 
                            lcd_d6, 
                            lcd_d7,
                            lcd_columns, 
                            lcd_rows, 
                            lcd_backlight,
                            gpio=gpio, 
                            initial_backlight=lcd_backlight_on)
    
    while True:
        ssid = os.popen("iwconfig wlan0 | awk -F '\"' '{print $2;exit}'").read()
        ipaddress = os.popen("ip route get 1 | awk '{print $NF;exit}'").read()
        lcd.clear()
        message = "{}{}".format(ssid, ipaddress)
        lcd.message(message)
        print message
    
        clocks.sleep(iprefresh_time_seconds)

if __name__ == "__main__":
    main()
