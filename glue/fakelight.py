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

import ephem

from neopixel import RectangularPixelMatrix
import numpy as np
import opc
from weather import WeatherUnderground


__app_name__ = "fakelight"

__verbose__ = [False]

# +----------------------------------------------------------------------------+
# | CURVE FUNCTIONS
# +----------------------------------------------------------------------------+

def sinusoidal(miny, maxy, period, x):
    return (maxy - miny) / 2 * math.sin(math.pi / (period / 2) * x - math.pi / 2) + (maxy + miny) / 2

def sinusoidal_uint8(period, x):
    return 127.5 * math.sin(math.pi / (period / 2.0) * x - math.pi / 2.0) + 127.5

def circular_rise(p):
    return math.sin(math.acos(1-p))

# +----------------------------------------------------------------------------+
# | CLOCKS
# +----------------------------------------------------------------------------+
class HyperClock(object):
    '''
    Fake clock that ticks at a programmable rate for use in debugging or for
    just doing funky things with the light over time.
    '''
    def __init__(self, muliplier=1000):
        self._hyper_now = ephem.now()
        self._last_tick = self._hyper_now
        self._multiplier = muliplier
        if __verbose__[0]:
            self._last_hour = ephem.date(self._hyper_now).tuple()[3]
            print "Using HyperClock"
    
    def now(self):
        real_now = ephem.now()
        elapsed = real_now - self._last_tick
        self._last_tick = real_now
        self._hyper_now += elapsed * self._multiplier
        if __verbose__[0]:
            hour = ephem.date(self._hyper_now).tuple()[3]
            if self._last_hour != hour:
                self._last_hour = hour
                print ephem.localtime(ephem.date(self._hyper_now))
            
        return self._hyper_now

class EphemWallClock(object):
    
    def now(self):
        return ephem.now()

# +----------------------------------------------------------------------------+
# | SKYS
# +----------------------------------------------------------------------------+

class WeatherSky(object):
    '''
    Pixel controller that represents the sky according to the time of day and
    weather conditions reported by an external weather service.
    '''
    def __init__(self, stride, pixel_count, cityname, wallclock, weather_service):
        if cityname is None:
            raise ValueError("cityname is required.")
        self._pixel_count = pixel_count
        self._stride = stride
        self._bg = 0.89
        self._rg = 1.0
        self._gg = 0.85
        self._clock = wallclock
        self._weather = weather_service
        self._observer = None
        self._sun = ephem.Sun()
        self._next_sunrise = None
        self._next_sunset = None
        self._next_day = None
        self._last_state = None
        self._last_reported_time = None
            
        try:
            self._observer = ephem.city(cityname)
            if __verbose__[0]:
                print "Skylight is installed in {}".format(cityname)
        except KeyError as e:
            # If you city is not found you can build an observer yourself.
            # See http://rhodesmill.org/pyephem/quick.html for details
            print str(e)
        except Exception as e:
            print str(e)
            print "pyephem is not working correctly."
    
    def weather_correct_sky_pixel(self):
        # TODO: change white value based on weather
        return (self._rg * 255, self._gg * 255, self._bg * 255)

    def _render_night(self, panel):
        panel.black()
    
    def _render_morning_twilight(self, panel):
        panel.red()
    
    def _render_evening_twilight(self, panel):
        panel.blue()
    
    def _render_daytime(self, panel):
        pixel = self.weather_correct_sky_pixel()
        panel.pixels = np.full((self._pixel_count, 3),
                   pixel, 
                   dtype=np.uint8)
    
    def _debug_state_changes(self, now, newstate):
        if __verbose__[0]:
            if self._last_state is None:
                print "Staring the sky in state: {}".format(newstate)
                self._last_state = newstate;
            elif newstate != self._last_state:
                print "entering: {}".format(newstate)
                self._last_state = newstate

            if self._last_reported_time is None or math.fabs(self._last_reported_time - now) > ephem.minute:
                self._last_reported_time = (now - (now % ephem.minute))
                print "The time is now {}".format(ephem.localtime(ephem.date(self._last_reported_time)))
    
    def _get_sunrise(self, now):
        if self._next_sunrise is None or now > self._next_sunrise[1]:
            self._observer.horizon = '0'
            rise = self._observer.next_rising(self._sun, start=now)
            self._observer.horizon = '-6'
            twilight = self._observer.next_rising(self._sun, start=now)
            if now < rise and math.fabs(twilight - rise) > ephem.hour * 12:
                # we are in the morning twilight
                twilight = self._observer.previous_rising(self._sun, start=now)

            self._next_sunrise = (twilight, rise)
            if __verbose__[0]:
                print "The sun will rise between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_sunrise[0])),
                    ephem.localtime(ephem.date(self._next_sunrise[1])))

        return self._next_sunrise

    def _get_sunset(self, now):
        if self._next_sunset is None or now > self._next_sunset[1]:
            self._observer.horizon = '-6'
            # TODO: add current temperature and pressure to calculate retraction
            darkness = self._observer.next_setting(self._sun, start=now)
            self._observer.horizon = '0'
            setting = self._observer.next_setting(self._sun, start=now)
            if now < setting and math.fabs(darkness - setting) > ephem.hour * 12:
                # we are in the evening twilight
                setting = self._observer.previous_setting(self._sun, start=now)
            
            self._next_sunset = (setting, darkness)
            
            if __verbose__[0]:
                print "The sun will set between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_sunset[0])),
                    ephem.localtime(ephem.date(self._next_sunset[1])))
                
        return self._next_sunset
    
    def _get_daylight(self, now):
        if self._next_day is None or now > self._next_day[1]:
            self._observer.horizon = '0'
            rising = self._observer.next_rising(self._sun, start=now)
            setting = self._observer.next_setting(self._sun, start=now)
            if now < setting and math.fabs(rising - setting) >= ephem.hour * 24:
                # we are in the day
                rising = self._observer.previous_rising(self._sun, start=now)
            
            self._next_day = (rising, setting)
            
            if __verbose__[0]:
                print "The sun will be up between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_day[0])),
                    ephem.localtime(ephem.date(self._next_day[1])))
                
        return self._next_day
    
    def __call__(self, panel):
        # morning twilight (-6 rising) = 0.0
        # morning sunrise (0 rising) = 1.0
        # evening sunset (0 setting) = 1.0
        # evening twilight (-6 setting) = 2.0
        # civil twilight
        now = self._clock.now()
        
        rising = self._get_sunrise(now)
        setting = self._get_sunset(now)
        daylight = self._get_daylight(now)
        
        if now > daylight[0] and now < daylight[1]:
            self._render_daytime(panel)
            self._debug_state_changes(now, "day")
        elif now <= setting[1] and now >= setting[0]:
            self._render_evening_twilight(panel)
            self._debug_state_changes(now, "evening_twilight")
        elif now >= rising[0] and now <= rising[1]:
            self._render_morning_twilight(panel)
            self._debug_state_changes(now, "morning_twilight")
        else:
            self._render_night(panel)
            self._debug_state_changes(now, "night")
            
# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+
_opc_fps = 240

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, 
            description="Open Pixel Controller client to simulate a skylight.")
    parser.add_argument('--address', default="127.0.0.1", help="IP address to connect to.")
    parser.add_argument('-p', '--port', help="TCP port to connect to OPC server on.", default=7890, type=int)
    parser.add_argument('-b', '--brightness', help="Linear brightness value (0 - 1.0)", default=1, type=float)
    parser.add_argument('--city', required=True, help="Weather underground city to get weather for.")
    parser.add_argument('--hyperday', action='store_true', help="Test mode that runs through 24 hours in less than a minute (but uses the current weather unless fake_conditions is provided)")
    parser.add_argument('--fake_conditions', help="Fake weather conditions for testing.")
    parser.add_argument('--verbose','-v', action='store_true', help="Spew debug stuff.")
    
    parser = WeatherUnderground.on_visit_argparse(parser)
    
    args = parser.parse_args()
    __verbose__[0] = args.verbose
    opc_client = opc.Client("{}:{}".format(args.address, args.port))
    
    while(not opc_client.can_connect()):
        print 'Waiting for {}...'.format(opc_client._port)
        time.sleep(1)
     
    print 'connected to {}'.format(opc_client._port)
    
    panel0 = RectangularPixelMatrix(opc_client, 0, 32, 512)
    panel0.brightness = args.brightness
    
    if args.hyperday:
        clock = HyperClock()
    else:
        clock = EphemWallClock()
        
    sky = WeatherSky(panel0.stride,
                     panel0.pixel_count, 
                     args.city, 
                     clock, 
                     WeatherUnderground(args))
    
    try:
        while(1):
            start = time.time()
            sky(panel0)
            delay_for = (1.0 / float(_opc_fps)) - (time.time() - start)
            time.sleep(delay_for if delay_for > 0 else 1)
    except KeyboardInterrupt:
        panel0.black()
    
    opc_client.disconnect()

if __name__ == "__main__":
    main()
