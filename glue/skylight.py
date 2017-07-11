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
# TODO:
# 1. Create a weather conditions -> colour map and implement _weather_correct_sky_pixel
# 2. setup.py
# 3. fake weather
# 4. Klaxon mode
# 5. curve tuning (maybe use scipy fitpack to generate splines?)
#
import argparse
import math
import time

from blessings import Terminal
import ephem

from clocks import HyperClock, WallClock
from curve_plot import plot_curve, make_curve
from lights import RectangularPixelMatrix
import opc
from weather import WeatherUnderground
from __builtin__ import None


__app_name__ = "skylight"
__standard_datetime_format_for_debug__ = "%Y/%m/%d %I:%M:%S %p"

# +----------------------------------------------------------------------------+
# | CURVE FUNCTIONS
# +----------------------------------------------------------------------------+

def sinusoidal(miny, maxy, period, x):
    return (maxy - miny) / 2 * math.sin(math.pi / (period / 2) * x - math.pi / 2) + (maxy + miny) / 2

def circular_rise(p, squish=1.0):
    return math.sin(math.acos(1-p)) * squish


# +----------------------------------------------------------------------------+
# | SKYS
# +----------------------------------------------------------------------------+

class WeatherSky(object):
    '''
    Pixel controller that represents the sky according to the time of day and
    weather conditions reported by an external weather service.
    '''
    
    def __init__(self, args, terminal, wallclock, weather_service):
        self._twilight = .5
        self._clock = wallclock
        self._city = args.city
        self._weather = weather_service
        self._observer = None
        self._sun = ephem.Sun()  # @UndefinedVariable
        self._next_sunrise = None
        self._next_sunset = None
        self._next_day = None
        self._next_night = None
        self._verbose = args.verbose
        self._show_daylight_chart = args.show_daylight_chart
        self._bterm = terminal
        self._weather_timer = None
        self._current_weather = None
        self._xy = None
        self._update_period_millis =  (3600000 * 24) / weather_service.get_max_updates_per_day() \
            if weather_service is not None else 0
            
        try:
            self._observer = ephem.city(self._city)
            if self._verbose:
                print "Skylight is installed in {}".format(self._city)
        except KeyError as e:
            # If you city is not found you can build an observer yourself.
            # See http://rhodesmill.org/pyephem/quick.html for details
            print str(e)
        except Exception as e:
            print str(e)
            print "pyephem is not working correctly."
    
    # +------------------------------------------------------------------------+
    # | PYTHON DATAMODEL
    # +------------------------------------------------------------------------+
    
    def __call__(self, panel):
        # morning twilight (-6 rising) = 0.0
        # morning sunrise (0 rising) = 1.0
        # evening sunset (0 setting) = 1.0
        # evening twilight (-6 setting) = 2.0
        # civil twilight
        now = self._clock.now()
        
        rising    = self._get_sunrise(now)
        daylight  = self._get_daylight(now)
        setting   = self._get_sunset(now)
        nighttime = self._get_night(now)
        
        if self._weather is not None:
            # We have to ensure we are always using wall-clock time for the
            # weather update since this API is metered.
            actually_now = time.time()
            if self._weather_timer is None or actually_now - self._weather_timer > self._update_period_millis:
                if self._verbose:
                    print "About to request new weather (The next request will be in {:.2f} minutes)".format(self._update_period_millis / 60000.00)
                # once per period send a request for new weather conditions
                self._weather.start_weather_update()
                self._weather_timer = actually_now
            
            if self._weather.has_new_weather():
                self._observer.pressure = self._weather.get_pressure_mb(self._observer.pressure)
                self._observer.temp = self._weather.get_temperature_c(self._observer.temp)
                self._current_weather = self._weather.get_current_weather()
                self._next_sunrise = None
                self._next_day = None
                self._next_sunset = None
                self._next_night = None
                self._xy = None
                if self._verbose:
                    print "Updating weather" 
        
        if now > daylight[0] and now < daylight[1]:
            phase = "day"
            progress = 1.0 - (daylight[1] - now) / (daylight[1] - daylight[0])
            self._render_daytime(panel, progress)
        elif now <= setting[1] and now >= setting[0]:
            phase = "evening twilight"
            progress = 1.0 - (setting[1] - now) / (setting[1] - setting[0])
            self._render_evening_twilight(panel, progress)
        elif now >= rising[0] and now <= rising[1]:
            phase = "morning twilight"
            progress = 1.0 - (rising[1] - now) / (rising[1] - rising[0])
            self._render_morning_twilight(panel, progress)
        else:
            phase = "night"
            progress = 1.0 - (nighttime[1] - now) / (nighttime[1] - nighttime[0])
            self._render_night(panel, progress)
        
        self._draw_debug(now, phase, progress)

    # +------------------------------------------------------------------------+
    # | LIGHTS
    # +------------------------------------------------------------------------+
    def _weather_correct_sky_pixel(self):
        # TODO: change white value based on weather
        return (255,255,255)

    def _render_night(self, panel, progress):  # @UnusedVariable
        # FUTURE: Render moon phase on a clear night
        panel.black()
    
    def _render_morning_twilight(self, panel, progress):
        panel.fill(tuple(x * circular_rise(progress, self._twilight) for x in self._weather_correct_sky_pixel()))
    
    def _render_evening_twilight(self, panel, progress):
        panel.fill(tuple(x * circular_rise(1.0 - progress, self._twilight) for x in self._weather_correct_sky_pixel()))
    
    def _render_daytime(self, panel, progress):
        panel.fill(tuple(x * sinusoidal(self._twilight, 1.0, 1.0, progress) for x in self._weather_correct_sky_pixel()))
    
    # +------------------------------------------------------------------------+
    # | EPHEMERIS
    # +------------------------------------------------------------------------+
    def _get_xy(self):
        if self._xy is None:
            morning_twilight = ephem.localtime(ephem.date(self._next_sunrise[0]))
            dawn = ephem.localtime(ephem.date(self._next_sunrise[1]))
            dusk = ephem.localtime(ephem.date(self._next_sunset[0]))
            dark = ephem.localtime(ephem.date(self._next_sunset[1]))
            self._xy = make_curve(
                morning_twilight.hour + (morning_twilight.minute / 60.0),
                dawn.hour             + (dawn.minute / 60.0),
                dusk.hour             + (dusk.minute / 60.0),
                dark.hour             + (dark.minute / 60.0))
        return self._xy
        
    def _get_sunrise(self, now):
        if self._next_sunrise is None or now > self._next_sunrise[1]:
            self._observer.horizon = '0'
            rise = self._observer.next_rising(self._sun, start=now)
            self._observer.horizon = '-6'
            twilight = self._observer.next_rising(self._sun, start=now)
            if now < rise and twilight > rise:
                # we are in the morning twilight
                twilight = self._observer.previous_rising(self._sun, start=now)

            self._next_sunrise = (twilight, rise)
            if self._verbose:
                print "The sun will rise between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_sunrise[0])).strftime(__standard_datetime_format_for_debug__),
                    ephem.localtime(ephem.date(self._next_sunrise[1])).strftime(__standard_datetime_format_for_debug__))

        return self._next_sunrise

    def _get_sunset(self, now):
        if self._next_sunset is None or now > self._next_sunset[1]:
            self._observer.horizon = '-6'
            # TODO: add current temperature and pressure to calculate retraction
            darkness = self._observer.next_setting(self._sun, start=now)
            self._observer.horizon = '0'
            setting = self._observer.next_setting(self._sun, start=now)
            if now < darkness and setting > darkness:
                # we are in the evening twilight
                setting = self._observer.previous_setting(self._sun, start=now)
            
            self._next_sunset = (setting, darkness)
            
            if self._verbose:
                print "The sun will set between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_sunset[0])).strftime(__standard_datetime_format_for_debug__),
                    ephem.localtime(ephem.date(self._next_sunset[1])).strftime(__standard_datetime_format_for_debug__))
                
        return self._next_sunset
    
    def _get_daylight(self, now):
        if self._next_day is None or now > self._next_day[1]:
            self._observer.horizon = '0'
            rising = self._observer.next_rising(self._sun, start=now)
            setting = self._observer.next_setting(self._sun, start=now)
            if now < setting and rising > setting:
                # we are in the day
                rising = self._observer.previous_rising(self._sun, start=now)
            
            self._next_day = (rising, setting)
            
            if self._verbose:
                print "The sun will be up between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_day[0])).strftime(__standard_datetime_format_for_debug__),
                    ephem.localtime(ephem.date(self._next_day[1])).strftime(__standard_datetime_format_for_debug__))
                
        return self._next_day
    
    def _get_night(self, now):
        if self._next_night is None or now > self._next_night[1]:
            self._xy = None
            self._observer.horizon = '-6'
            setting = self._observer.next_setting(self._sun, start=now)
            rising = self._observer.next_rising(self._sun, start=now)
            if now < rising and setting > rising:
                # we are in the night
                setting = self._observer.previous_setting(self._sun, start=now)
            
            self._next_night = (setting, rising)
            
            if self._verbose:
                print "The sun will be down between {} and {}".format(
                    ephem.localtime(ephem.date(self._next_night[0])).strftime(__standard_datetime_format_for_debug__),
                    ephem.localtime(ephem.date(self._next_night[1])).strftime(__standard_datetime_format_for_debug__))
                
        return self._next_night
    
    # +------------------------------------------------------------------------+
    # | DEBUG/UTILITY
    # +------------------------------------------------------------------------+
    
    def _draw_debug(self, now, phase, progress):
        if self._verbose:
            with self._bterm.location(0, 0):
                self._bterm.clear_eol()
                rhs =  "[{phase}] {progress:.0%}".format(phase=phase,
                                      progress=progress)
                center = "weather: {}".format(self._current_weather)
                lhs = "{city}: {now:50}".format(city=self._city, 
                                      now=ephem.localtime(ephem.date(now)).strftime(__standard_datetime_format_for_debug__))
                spacing = (self._bterm.width - (len(rhs) + len(lhs) + len(center)))
                lspacing = int(round(spacing / 2, 0))
                rspacing = spacing - lspacing
                print self._bterm.white_on_blue("{}{}{}{}{}".format(lhs, ' ' * lspacing , center, ' ' * rspacing, rhs))
        if self._show_daylight_chart:
            plot_curve(self._get_xy())
            self._show_daylight_chart = False

# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+
_opc_fps = 240

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, 
            description="Open Pixel Controller client providing contextual lighting effects.")
    
    subparsers = parser.add_subparsers(dest="command", help="Clock Modes")
    
    eph_args = parser.add_argument_group('Ephemeris options')
    eph_args.add_argument('--city', required=True, help="A city used to lookup ephemeris values and to retrieve current weather conditions.")
    
    opc_args = parser.add_argument_group('OPC options')
    opc_args.add_argument('--address', default="127.0.0.1", help="IP address to connect to.")
    opc_args.add_argument('-p', '--port', help="TCP port to connect to OPC server on.", default=7890, type=int)
    
    debug_args = parser.add_argument_group('debug options')
    debug_args.add_argument('--verbose','-v', action='store_true', help="Spew debug stuff.")
    debug_args.add_argument('--show-daylight-chart', '-D', action='store_true', help="Open a window showing a plot of the daylight curve in-use.")
    
    RectangularPixelMatrix.on_visit_argparse(parser, subparsers)
    HyperClock.on_visit_argparse(parser, subparsers)
    WallClock.on_visit_argparse(parser, subparsers)
    
    WeatherUnderground.on_visit_argparse(parser, subparsers)
    
    terminal = Terminal()
    args = parser.parse_args()
    opc_client = opc.Client("{}:{}".format(args.address, args.port))
    
    dots = ''
    while(not opc_client.can_connect()):
        with terminal.location(0, terminal.height - 2):
            print 'Waiting for OPC server {}{:8}'.format(opc_client._port, dots)
        dots = dots + '.' if len(dots) < 8 else '.'
        time.sleep(1)
    
    try:
        print 'connected to OPC server on {}'.format(opc_client._port)
        
        panel0 = RectangularPixelMatrix(args, opc_client)
        
        clock = args.func(args)
        
        try:
            weather = WeatherUnderground(args)
        except ValueError:
            print "Unable to obtain weather information. Check commandline arguments."
            weather = None
            
        sky = WeatherSky(args, 
                         terminal,
                         clock, 
                         weather)
        try:
            while(1):
                start = time.time()
                sky(panel0)
                delay_for = (1.0 / float(_opc_fps)) - (time.time() - start)
                time.sleep(delay_for if delay_for > 0 else 1)
        except KeyboardInterrupt:
            panel0.black()
            
    finally:
        opc_client.disconnect()

if __name__ == "__main__":
    main()
