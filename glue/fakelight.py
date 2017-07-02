#!/usr/bin/env python

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
   
#  ___       _                       _     ____  _          _ _       _     _   
# |_ _|_ __ | |_ ___ _ __ _ __   ___| |_  / ___|| | ___   _| (_) __ _| |__ | |_ 
#  | || '_ \| __/ _ \ '__| '_ \ / _ \ __| \___ \| |/ / | | | | |/ _` | '_ \| __|
#  | || | | | ||  __/ |  | | | |  __/ |_   ___) |   <| |_| | | | (_| | | | | |_ 
# |___|_| |_|\__\___|_|  |_| |_|\___|\__| |____/|_|\_\\__, |_|_|\__, |_| |_|\__|
#                                                     |___/     |___/

import argparse
import math
import time

from neopixel import RectangularPixelMatrix
import numpy as np
import opc

import json
import requests
import ephem

__app_name__ = "fakelight"

def sinusoidal(miny, maxy, period, x):
    return (maxy - miny) / 2 * math.sin(math.pi / (period / 2) * x - math.pi / 2) + (maxy + miny) / 2

def sinusoidal_uint8(period, x):
    return 127.5 * math.sin(math.pi / (period / 2.0) * x - math.pi / 2.0) + 127.5

def circular_rise(p):
    return math.sin(math.acos(1-p))
        

class Sky(object):
    
    def __init__(self, stride, pixel_count, cityname):
        self._pixel_count = pixel_count
        self._stride = stride
        self._x = 0.00
        self._bg = 0.89
        self._rg = 1.0
        self._gg = 0.85
        self._observer = None
        self._rise = True
        if cityname is not None:
            try:
                self._observer = ephem.city(cityname)
            except KeyError as e:
                # If you city is not found you can build an observer yourself.
                # See http://rhodesmill.org/pyephem/quick.html for details
                print str(e)
            except Exception as e:
                print str(e)
                print "pyephem is not working correctly."
    
    def weather_correct_sky_pixel(self, white_point):
        # TODO: change white value based on weather
        return (white_point[0] * self._rg, white_point[1] * self._gg, white_point[2] * self._bg)

    def get_pixel_for_time_of_day(self):
        # TODO: change white value based on the current time
        wp = sinusoidal_uint8(1, self._x)
        return (0, 0, 255)
    
    def __call__(self, panel):
        sun = ephem.Sun()
        now = ephem.now()
        # morning twilight (-6 rising) = 0.0
        # morning sunrise (0 rising) = 1.0
        # evening sunset (0 setting) = 1.0
        # evening twilight (-6 setting) = 2.0
        # civil twilight
        self._observer.horizon = '-6'
        next_rising = self._observer.next_rising(sun, use_center=True)
        next_setting = self._observer.next_setting(sun, use_center=True)
        self._x += (0.001 if self._rise else -0.001)
        if self._x >= 1.0:
            self._rise = False
            self._x = 1.0
        elif self._x <= 0.0:
            self._rise = True
            self._x = 0.0
            
        pixel = round(circular_rise(self._x) * 255.00, 0)
        panel.pixels = np.full((self._pixel_count, 3),
                   pixel, 
                   dtype=np.uint8)
            
        
    
class Weather(object):
    
    EMERGENCY_WEATHER = {}
    CRAPPY_WEATHER = { "(Light|Heavy) Drizzle" }
    NOT_SUNNY_WEATHER = {}
    SNOWING = {}
    SUNNY_WEATHER = {}
    
    '''   
    [Light/Heavy] Rain
    [Light/Heavy] Snow
    [Light/Heavy] Snow Grains
    [Light/Heavy] Ice Crystals
    [Light/Heavy] Ice Pellets
    [Light/Heavy] Hail
    [Light/Heavy] Mist
    [Light/Heavy] Fog
    [Light/Heavy] Fog Patches
    [Light/Heavy] Smoke
    [Light/Heavy] Volcanic Ash
    [Light/Heavy] Widespread Dust
    [Light/Heavy] Sand
    [Light/Heavy] Haze
    [Light/Heavy] Spray
    [Light/Heavy] Dust Whirls
    [Light/Heavy] Sandstorm
    [Light/Heavy] Low Drifting Snow
    [Light/Heavy] Low Drifting Widespread Dust
    [Light/Heavy] Low Drifting Sand
    [Light/Heavy] Blowing Snow
    [Light/Heavy] Blowing Widespread Dust
    [Light/Heavy] Blowing Sand
    [Light/Heavy] Rain Mist
    [Light/Heavy] Rain Showers
    [Light/Heavy] Snow Showers
    [Light/Heavy] Snow Blowing Snow Mist
    [Light/Heavy] Ice Pellet Showers
    [Light/Heavy] Hail Showers
    [Light/Heavy] Small Hail Showers
    [Light/Heavy] Thunderstorm
    [Light/Heavy] Thunderstorms and Rain
    [Light/Heavy] Thunderstorms and Snow
    [Light/Heavy] Thunderstorms and Ice Pellets
    [Light/Heavy] Thunderstorms with Hail
    [Light/Heavy] Thunderstorms with Small Hail
    [Light/Heavy] Freezing Drizzle
    [Light/Heavy] Freezing Rain
    [Light/Heavy] Freezing Fog
    Patches of Fog
    Shallow Fog
    Partial Fog
    Overcast
    Clear
    Partly Cloudy
    Mostly Cloudy
    Scattered Clouds
    Small Hail
    Squalls
    Funnel Cloud
    Unknown Precipitation
    Unknown
    '''
    
    def __init__(self, api_key):
        self._key = api_key
    
    def get_current_conditions(self, city):
        r = requests.get("http://api.wunderground.com/api/{}/conditions/q/CA/{}.json".format(self._key, city))
        return r.json()
    
    def get_current_weather(self, city):
        return self.get_current_conditions(city)['current_observation']['weather']
    
    def print_complete_weather(self, city):
        print json.dumps(self.get_current_conditions(city), indent=4, sort_keys=True)
        
# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+
_opc_fps = 240

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, description="Open Pixel Controller client to simulate a skylight.")
    parser.add_argument('--address', default="127.0.0.1", help="IP address to connect to.")
    parser.add_argument('-p', '--port', help="TCP port to connect to OPC server on.", default=7890, type=int)
    parser.add_argument('-b', '--brightness', help="Linear brightness value (0 - 1.0)", default=1, type=float)
    parser.add_argument('--wukey', help="API key for the weather underground")
    parser.add_argument('--city', help="Weather underground city to get weather for.")
    
    args = parser.parse_args()
    
    
    opc_client = opc.Client("{}:{}".format(args.address, args.port))
    
    while(not opc_client.can_connect()):
        print 'Waiting for {}...'.format(opc_client._port)
        time.sleep(1)
     
    print 'connected to {}'.format(opc_client._port)
    
    panel0 = RectangularPixelMatrix(opc_client, 0, 32, 512)
    panel0.brightness = args.brightness
    ani0 = Sky(panel0.stride, panel0.pixel_count, args.city)
    
    w = Weather(args.wukey)
    
    try:
        print w.get_current_weather(args.city)
        while(1):
            start = time.time()
            ani0(panel0)
            delay_for = (1.0 / float(_opc_fps)) - (time.time() - start)
            time.sleep(delay_for if delay_for > 0 else 1)
    except KeyboardInterrupt:
        panel0.black()
    
    opc_client.disconnect()

if __name__ == "__main__":
    main()
