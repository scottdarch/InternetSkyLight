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

# +---------------------------------------------------------------------+
class LCDCape(object):
    
    PAGE_COUNT = 3
    FORMAT_FOR_CLOCK = "%m/%d/%y %I:%M %p"
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers=None):  # @UnusedVariable
        parser.add_argument("--interface", default="eth0", help="The interface to report the address for.")

    def __init__(self, args, sky=None):

        self._last_refresh = 0
        self._interface = args.interface
        self._verbose = args.verbose if hasattr(args, "verbose") else False
        self._page = -1
        self._page_delay_seconds = 5
        self._is_wlan = True if re.match("^eth", self._interface) is None else False
        self._sky = sky
        
        try:
            import Adafruit_CharLCD as LCD
            import Adafruit_GPIO.MCP230xx as MCP
            
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
        except IOError:
            self._lcd = None
            
    def __call__(self):
        now = time.time()
        if now - self._last_refresh < self._page_delay_seconds:
            return
        self._last_refresh = now
        
        self._page += 1
        if self._page == self.PAGE_COUNT:
            self._page = 0
        
        page_method = getattr(self,"_show_page{}".format(self._page))
        
        message = page_method()
        if self._verbose:
            print "LCD CAPE PAGE {}:".format(self._page)
            print "----------------"
            print message
            print "----------------"
        
        if self._lcd is not None:
            self._lcd.clear()
            self._lcd.message(message)
    
    def _show_page0(self):
        if self._is_wlan:
            return "{}\n{}".format(self._wlan_ssid(self._interface), self._wlan_address(self._interface))
        else:
            return "{}\n{}".format(self._interface, self._ethernet_address(self._interface))
    
    def _show_page1(self):
        if self._sky is None:
            return "(pg1: NO DATA)"
        else:
            return "{}\n{}".format(self._sky.get_sky_time(self.FORMAT_FOR_CLOCK), self._sky.get_sky_weather())
    
    def _show_page2(self):
        if self._sky is None:
            return "(pg2: NO DATA)"
        else:
            return "{}\n{:.0%}".format(self._sky.get_sky_phase(), self._sky.get_sky_progress())
    
    def _ethernet_address(self, interface):
        return os.popen("ip addr show " + interface + " | awk '$1 == \"inet\" {gsub(/\/.*$/, \"\", $2); print $2}'").read()
    
    def _wlan_ssid(self, interface):
        return os.popen("iwconfig " + interface + " | awk -F '\"' '{print $2;exit}'").read()
    
    def _wlan_address(self, interface):  # @UnusedVariable
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
        time.sleep(1)

if __name__ == "__main__":
    main()
