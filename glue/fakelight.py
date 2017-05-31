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

from neopixel import SquarePixelMatrix
import numpy as np
import opc


__app_name__ = "fakelight"

def sinusoidal(miny, maxy, period, x):
    return (maxy - miny) / 2 * math.sin(math.pi / (period / 2) * x - math.pi / 2) + (maxy + miny) / 2

def sinusoidal_uint8(period, x):
    return 127.5 * math.sin(math.pi / (period / 2) * x - math.pi / 2) + 127.5


class Sky(object):
    
    def __init__(self, stride, pixel_count):
        self._pixels = np.zeros((pixel_count, 3), dtype=np.uint8)
        self._pixel_count = pixel_count
        self._stride = stride
        self._x = 0
        self._bg = 1.0
        self._rg = 0.8
        self._gg = 0.9
    
    def weather_correct_sky_pixel(self, white_point):
        # TODO: change white value based on weather
        return (white_point[0] * self._rg, white_point[1] * self._gg, white_point[2] * self._bg)

    def get_pixel_for_time_of_day(self):
        # TODO: change white value based on the current time
        wp = sinusoidal_uint8(500, self._x)
        return (wp, wp, wp)
    
    def __call__(self, panel):
        
        self._pixels = np.full((self._pixel_count, 3), 
                               self.weather_correct_sky_pixel(self.get_pixel_for_time_of_day()), 
                               dtype=np.uint8)
        panel.set_pixels(self._pixels)
    
# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+
_opc_fps = 120

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, description="Open Pixel Controller client to simulate a skylight.")
    parser.add_argument('-p', '--port', help="TCP port to connect to OPC server on.", default=7890, type=int)
    
    args = parser.parse_args()
    
    
    opc_client = opc.Client("127.0.0.1:{}".format(args.port))
    
    while(not opc_client.can_connect()):
        print 'Waiting for {}...'.format(opc_client._port)
        time.sleep(1)
     
    print 'connected to {}'.format(opc_client._port)
    
    panel0 = SquarePixelMatrix(opc_client, 0, 64)
    ani0 = Sky(panel0.pixel_count/2, panel0.pixel_count)
    
    try:

        while(1):
            start = time.time()
            ani0(panel0)
            time.sleep((1.0 / float(_opc_fps)) - (time.time() - start))
    except KeyboardInterrupt:
        panel0.black()
    
    opc_client.disconnect()

if __name__ == "__main__":
    main()
