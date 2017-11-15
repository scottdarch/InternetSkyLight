#
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
import json
import re
import threading

import requests


class WeatherUnderground(object):
    
    MAX_API_CALLS_PER_DAY = 400
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers):  # @UnusedVariable
        group = parser.add_argument_group("weather options")
        group.add_argument('--wukey', help="API key for the weather underground")
        group.add_argument('--weather', default=None, help="Fake weather conditions for testing.")
    
    EMERGENCY_WEATHER   = { "(light|heavy) Hail",
                            "(light|heavy) Volcanic Ash",
                            "(light|heavy) Smoke",
                            "(light|heavy) Sandstorm",
                            "(light|heavy) Hail Showers",
                            "(light|heavy) Thunderstorms with Hail"}
    NOT_SUNNY_WEATHER   = { "(light|heavy) Rain",
                            "(light|heavy) Drizzle",
                            "(light|heavy) Ice Crystals",
                            "(light|heavy) Ice Pellets",
                            "(light|heavy) Mist",
                            "(light|heavy) Fog",
                            "(light|heavy) Fog Patches",
                            "(light|heavy) Widespread Dust",
                            "(light|heavy) Sand",
                            "(light|heavy) Haze",
                            "(light|heavy) Spray",
                            "(light|heavy) Dust Whirls",
                            "(light|heavy) Low Drifting Snow",
                            "(light|heavy) Low Drifting Widespread Dust",
                            "(light|heavy) Low Drifting Sand",
                            "(light|heavy) Blowing Snow",
                            "(light|heavy) Blowing Widespread Dust",
                            "(light|heavy) Blowing Sand",
                            "(light|heavy) Rain Mist",
                            "(light|heavy) Rain Showers",
                            "(light|heavy) Ice Pellet Showers",
                            "(light|heavy) Small Hail Showers",
                            "(light|heavy) Thunderstorm",
                            "(light|heavy) Thunderstorms and Rain",
                            "(light|heavy) Thunderstorms and Snow",
                            "(light|heavy) Thunderstorms and Ice Pellets",
                            "(light|heavy) Thunderstorms with Small Hail",
                            "(light|heavy) Freezing Drizzle",
                            "(light|heavy) Freezing Rain",
                            "(light|heavy) Freezing Fog",
                            "Patches of Fog",
                            "Shallow Fog",
                            "Partial Fog",
                            "Overcast",
                            "Small Hail",
                            "Squalls",
                            "Unknown Precipitation",
                            "Unknown",
                            "Funnel Cloud"
                          }
    SNOWING             = { "(light|heavy) Snow",
                            "(light|heavy) Snow Grains",
                            "(light|heavy) Snow Showers",
                            "(light|heavy) Snow Blowing Snow Mist",
                            "Snow",
                            "Snowing"
                          }
    SUNNY_WEATHER       = { "Clear",
                            "Sunny",
                            "Sun",
                            "Partly Cloudy",
                            "Mostly Cloudy",
                            "Scattered Clouds"
                          }
    
    @staticmethod
    def _request_routine(self):
        if self._fake_weather is not None:
            conditions = { 'current_observation': {'weather': self._fake_weather}}
        else:
            r = requests.get("http://api.wunderground.com/api/{}/conditions/q/CA/{}.json".format(self._key, self._city))
            conditions = r.json()
        with self._request_lock:
            if self._verbose:
                print "New conditions received: {}".format(conditions)
            self._conditions = conditions
            self._new_data_flag = True

    def __init__(self, args):
        self._key = args.wukey
        self._city = args.city
        self._conditions = None
        self._verbose = args.verbose
        self._request_thread = None
        self._request_lock = threading.RLock()
        self._new_data_flag = False
        self._fake_weather = args.weather
        if self._fake_weather is None:
            if self._key is None:
                raise ValueError("wukey argument is required if not using fake conditions.")
        elif self._verbose:
            print "Using fake weather conditions {}".format(self._fake_weather)
    
    def get_max_updates_per_day(self):
        return self.MAX_API_CALLS_PER_DAY
    
    def start_weather_update(self):
        with self._request_lock:
            if self._request_thread is None or not self._request_thread.is_alive():
                self._request_thread = threading.Thread(group=None, target=self._request_routine, args=[self])
                self._request_thread.start()
                return True
            else:
                return False

    def has_new_weather(self):
        with self._request_lock:
            return self._new_data_flag
    
    @property
    def is_sunny(self):
        conditions = self.get_current_conditions()
        if conditions is None:
            return False
        else:
            return self._is_weather(self.SUNNY_WEATHER, conditions['weather'])
    
    @property
    def is_snowing(self):
        conditions = self.get_current_conditions()
        if conditions is None:
            return True
        else:
            return self._is_weather(self.SNOWING, conditions['weather'])
    
    @property
    def is_emergency(self):
        # TODO: use weather alerts from the API instead of classifying conditions.
        conditions = self.get_current_conditions()
        if conditions is None:
            return True
        else:
            return self._is_weather(self.EMERGENCY_WEATHER, conditions['weather'])
        
    def get_current_conditions(self):
        with self._request_lock:
            self._new_data_flag = False
            return (self._conditions['current_observation'] if self._conditions is not None else None)
    
    def get_current_weather(self):
        conditions = self.get_current_conditions()
        return (conditions['weather'] if conditions is not None else None)
    
    def get_pressure_mb(self, default_value=1013.25):
        try:
            conditions = self.get_current_conditions()
            return (float(conditions['pressure_mb']) if conditions is not None else default_value)
        except KeyError:
            return default_value

    def get_temperature_c(self, default_value=0.0):
        try:
            conditions = self.get_current_conditions()
            return (float(conditions['temp_c']) if conditions is not None else default_value)
        except KeyError:
            return default_value
    
    def print_complete_weather(self):
        print json.dumps(self.get_current_conditions(), indent=4, sort_keys=True)
    
    # +-----------------------------------------------------------------+
    # | PRIVATE
    # +-----------------------------------------------------------------+
    @staticmethod
    def _is_weather(pattern_map, current_weather):
        for weather in pattern_map:
            if re.match(weather, current_weather, re.IGNORECASE):
                return True
        return False
        
