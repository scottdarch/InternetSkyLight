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
#
import argparse
import time

import ephem

from clocks import HyperClock, WallClock
from curve_plot import plot_curve, make_curve
from lcd_cape import LCDCape
from lights import RectangularPixelMatrix
import opc
from weather import WeatherUnderground


__app_name__ = "skylight"
__standard_datetime_format_for_debug__ = "%Y/%m/%d %I:%M:%S %p"

# +----------------------------------------------------------------------------+
# | SKYS
# +----------------------------------------------------------------------------+
class Daylight(object):
    
    def __init__(self, twilight, dawn, dusk, dark, xy):
        self._twilight = twilight
        self._dawn = dawn
        self._dusk = dusk
        self._dark = dark
        self._xy = xy
    
    @property
    def twilight(self):
        return self._twilight
    
    @property
    def dawn(self):
        return self._dawn
    
    @property
    def dusk(self):
        return self._dusk
    
    @property
    def dark(self):
        return self._dark
    
    @property
    def intensities(self):
        return self._xy[1]
    
    @property
    def day_curve(self):
        return self._xy
    
    def progress(self, now):
        if self.is_daylight(now):
            return (now - self._twilight) / (self._dark - self._twilight)
        else:
            return (self._twilight - now) / (1 - (self._dark - self._twilight))
        
    def is_daylight(self, now):
        return now >= self._twilight and now <= self._dark
    
    def get_phase_for(self, now):
        if now < self._twilight:
            return "night"
        elif now < self._dawn:
            return "morning twilight"
        elif now < self._dusk:
            return "daytime"
        elif now < self._dark:
            return "evening twilight"
        else:
            return "night"

class WeatherSky(object):
    '''
    Pixel controller that represents the sky according to the time of day and
    weather conditions reported by an external weather service.
    '''
    
    def __init__(self, args, wallclock, weather_service):
        self._twilight = "-7"
        self._clock = wallclock
        self._city = args.city
        self._weather = weather_service
        self._observer = None
        self._sun = ephem.Sun()  # @UndefinedVariable
        self._verbose = args.verbose
        self._show_daylight_chart = args.show_daylight_chart
        self._weather_timer = None
        self._current_daylight = None
        self._pixel_color = (255,255,255)
        self._last_clock_time = self._clock.now()
        
        self._update_period_seconds =  (3600 * 24) / weather_service.get_max_updates_per_day() \
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
        now = self._clock.now()
        
        if self._weather is not None:
            # We have to ensure we are always using wall-clock time for the
            # weather update since this API is metered.
            actually_now_seconds = time.time()
            if self._weather_timer is None or actually_now_seconds - self._weather_timer > self._update_period_seconds:
                if self._verbose:
                    print "About to request new weather (The next request will be in {:.2f} minutes)".format(self._update_period_seconds / 60.00)
                # once per period send a request for new weather conditions
                self._weather.start_weather_update()
                self._weather_timer = actually_now_seconds
            
            if self._weather.has_new_weather():
                self._observer.pressure = self._weather.get_pressure_mb(self._observer.pressure)
                self._observer.temp = self._weather.get_temperature_c(self._observer.temp)
                if self._weather.is_sunny:
                    self._pixel_color = (255,255,255)
                elif self._weather.is_emergency:
                    # TODO: strobe or other animation for "alert, bad weather!"
                    self._pixel_color = (255,0,0)
                elif self._weather.is_snowing:
                    # TODO: something more festive for snow.
                    self._pixel_color = (0,255,0)
                else:
                    self._pixel_color = (0,0,255)
                
                self._current_daylight = None
                if self._verbose:
                    print "Updating weather" 
        
        self._update_ephemeris(now)
        
        intensities = self._current_daylight.intensities

        progress = self._current_daylight.progress(now)
        
        if self._current_daylight.is_daylight(now):
        
            intensity_index = int(len(intensities) * progress)
            self._render_daylight(panel, intensities[intensity_index if intensity_index < len(intensities) else len(intensities) - 1])
        else:
            self._render_night(panel, progress)
        
        self._last_clock_time = now
        
        self._draw_debug()

    # +------------------------------------------------------------------------+
    # | LIGHTS
    # +------------------------------------------------------------------------+
    def _weather_correct_sky_pixel(self):
        return self._pixel_color

    def _render_night(self, panel, progress):  # @UnusedVariable
        # FUTURE: Render moon phase on a clear night
        panel.black()
    
    def _render_daylight(self, panel, intensity):
        panel.fill(tuple(x * (intensity if intensity <= 1.0 else 1.0) for x in self._weather_correct_sky_pixel()))
    
    # +------------------------------------------------------------------------+
    # | EPHEMERIS
    # +------------------------------------------------------------------------+
    def _update_ephemeris(self, now):
        
        self._observer.horizon = self._twilight
        next_dark = self._observer.next_setting(self._sun, start=now)
        
        if self._current_daylight is None or int(next_dark) != int(self._current_daylight.dark):
            
            twilight = self._observer.previous_rising(self._sun, start=next_dark)
            
            self._observer.horizon = '0'
            dawn = self._observer.next_rising(self._sun, start=twilight)
            dusk = self._observer.next_setting(self._sun, start=twilight)
            xy = make_curve(float(twilight), float(dawn), float(dusk), float(next_dark))
            if self._verbose:
                print "It's a new day ({} - {})".format(twilight, next_dark)
            self._current_daylight = Daylight(twilight, dawn, dusk, next_dark, xy)            
    
    # +------------------------------------------------------------------------+
    # | DEBUG/UTILITY
    # +------------------------------------------------------------------------+
    def get_sky_time(self, time_format):
        return ephem.localtime(ephem.date(self._last_clock_time)).strftime(time_format)
    
    def get_sky_phase(self):
        if None == self._current_daylight:
            return "(none)"
        else:
            return self._current_daylight.get_phase_for(self._last_clock_time)
    
    def get_sky_progress(self):
        if None == self._current_daylight:
            return "(none)"
        else:
            return self._current_daylight.progress(self._last_clock_time)

    def get_sky_weather(self):
        if self._weather is not None:
            return self._weather.get_current_weather()
        else:
            return "(no data)"
        
    def _draw_debug(self):
        if self._verbose:
            rhs =  "[{phase}] {progress:.0%}".format(phase=self.get_sky_phase(),
                                  progress=self.get_sky_progress())
            center = "weather: {}".format(self.get_sky_weather())
            lhs = "{city}: {now:50}".format(city=self._city, 
                                  now=self.get_sky_time(__standard_datetime_format_for_debug__))
            print "{} | {} | {}".format(lhs, center, rhs)
        if self._show_daylight_chart:
            plot_curve(self._current_daylight.day_curve, self._current_daylight.dawn, self._current_daylight.dusk)
            self._show_daylight_chart = False

# +---------------------------------------------------------------------------+
# | MAIN
# +---------------------------------------------------------------------------+

def main():
    parser = argparse.ArgumentParser(
            prog=__app_name__, 
            description="Open Pixel Controller client providing contextual lighting effects.")
    
    parser.add_argument("--frame-rate", default=1, type=int, help="Frames-per-second to run the sky simulation at.")
    
    subparsers = parser.add_subparsers(dest="command", help="Clock Modes")
    
    eph_args = parser.add_argument_group('Ephemeris options')
    eph_args.add_argument('--city', required=True, help="A city used to lookup ephemeris values and to retrieve current weather conditions.")
    
    debug_args = parser.add_argument_group('debug options')
    debug_args.add_argument('--verbose','-v', action='store_true', help="Spew debug stuff.")
    debug_args.add_argument('--show-daylight-chart', '-D', action='store_true', help="Open a window showing a plot of the daylight curve in-use.")
    debug_args.add_argument('--opc-dont-connect', '-X', action='store_true', help="Skip trying to connect to an OPC server. Allows testing other parts of the skylight without actually running the LEDs.")
    
    RectangularPixelMatrix.on_visit_argparse(parser, subparsers)
    HyperClock.on_visit_argparse(parser, subparsers)
    WallClock.on_visit_argparse(parser, subparsers)
    opc.Client.on_visit_argparse(parser, subparsers)
    LCDCape.on_visit_argparse(parser, subparsers)
        
    WeatherUnderground.on_visit_argparse(parser, subparsers)
    
    args = parser.parse_args()
    opc_client = opc.Client(args)
    
    if not args.opc_dont_connect:
        dots = ''
        while(not opc_client.can_connect()):
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
                         clock, 
                         weather)
        
        cape = LCDCape(args, sky)
        
        fps = args.frame_rate
        if args.verbose:
            print "Running the simulation at {} frame(s) per second".format(fps)
        try:
            while(1):
                start = time.time()
                sky(panel0)
                cape()
                delay_for = (1.0 / float(fps)) - (time.time() - start)
                time.sleep(delay_for if delay_for > 0 else 1)
        except KeyboardInterrupt:
            panel0.black()
            
    finally:
        opc_client.disconnect()

if __name__ == "__main__":
    main()
