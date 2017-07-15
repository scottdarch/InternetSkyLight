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

import argparse
import os
import re

import Adafruit_CharLCD as LCD
import Adafruit_GPIO.MCP230xx as MCP
import time


__app_name__ = "lcd_cape"

# +---------------------------------------------------------------------+
# | CONSTANTS
# +---------------------------------------------------------------------+

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

refresh_time_seconds = 5

# +---------------------------------------------------------------------+
class LCDCape(object):
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers=None):  # @UnusedVariable
        parser.add_argument("--interface", default="eth0", help="The interface to report the address for.")

    def __init__(self, args):
        self._last_refresh = time.time()
        self._interface = args.interface
        # Initialize MCP23017 device using its default 0x20 I2C address.
        gpio = MCP.MCP23008(busnum=2)
    
        # Initialize the LCD using the pins
        self._lcd = LCD.Adafruit_CharLCD(
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
    
    def __call__(self):
        now = time.time()
        if now - self._last_refresh < refresh_time_seconds:
            return
        self._last_refresh = now
        if re.match("^eth", self._interface) is not None:
            line0 = self._line0_ethernet
            line1 = self._line1_ethernet
        else:
            line0 = self._line0_wlan
            line1 = self._line1_wlan
            
        self._lcd.clear()
        message = "{}\n{}".format(line0(self._interface), line1(self._interface))
        self._lcd.message(message)
            
    def _line0_ethernet(self, interface):
        return interface
    
    def _line1_ethernet(self, interface):
        return os.popen("ip addr show " + interface + " | awk '$1 == \"inet\" {gsub(/\/.*$/, \"\", $2); print $2}'").read()
    
    def _line0_wlan(self, interface):
        return os.popen("iwconfig " + interface + " | awk -F '\"' '{print $2;exit}'").read()
    
    def _line1_wlan(self, interface):  # @UnusedVariable
        return os.popen("ip route get 1 | awk '{print $NF;exit}'").read()
        
    
# +---------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------+

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, 
            description="Runs a 16 character display attached to the BeagleBone to display the current IP address.")
    
    LCDCape.on_visit_argparse(parser)
    
    args = parser.parse_args()
     
    cape = LCDCape(args)
    
    while(True):
        cape()
        time.sleep(refresh_time_seconds / 4)

if __name__ == "__main__":
    main()
