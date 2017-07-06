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
#
import json
import threading

import requests


class WeatherUnderground(object):
    
    MAX_API_CALLS_PER_DAY = 400
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers):  # @UnusedVariable
        group = parser.add_argument_group("weather options")
        group.add_argument('--wukey', help="API key for the weather underground")
        group.add_argument('--fake_conditions', help="Fake weather conditions for testing.")
    
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
    
    @staticmethod
    def _request_routine(self):
        r = requests.get("http://api.wunderground.com/api/{}/conditions/q/CA/{}.json".format(self._key, self._city))
        conditions = r.json()
        with self._request_lock:
            self._conditions = conditions
            self._new_data_flag = True

    def __init__(self, args):
        self._key = args.wukey
        if self._key is None:
            raise ValueError("wukey argument is required if not using fake conditions.")
        self._city = args.city
        self._conditions = None
        self._verbose = args.verbose
        self._request_thread = None
        self._request_lock = threading.RLock()
        self._new_data_flag = False
    
    def get_max_updates_per_day(self):
        return self.MAX_API_CALLS_PER_DAY
    
    def start_weather_update(self):
        with self._request_lock:
            if self._request_thread is None or self._request_lock.is_alive():
                self._request_thread = threading.Thread(group=None, target=self._request_routine, args=[self])
                self._request_thread.start()
                return True
            else:
                return False

    def has_new_weather(self):
        has_new = False
        with self._request_lock:
            has_new = self._new_data_flag
            self._new_data_flag = False
            #if self._verbose:
            #    self.print_complete_weather()
        return has_new
        
    def get_current_conditions(self):
        with self._request_lock:
            return (self._conditions['current_observation'] if self._conditions is not None else None)
    
    def get_current_weather(self):
        conditions = self.get_current_conditions()
        return (conditions['weather'] if conditions is not None else None)
    
    def get_pressure_mb(self, default_value=1013.25):
        conditions = self.get_current_conditions()
        return (float(conditions['pressure_mb']) if conditions is not None else default_value)
    
    def get_temperature_c(self, default_value=0.0):
        conditions = self.get_current_conditions()
        return (float(conditions['temp_c']) if conditions is not None else default_value)
    
    def print_complete_weather(self):
        print json.dumps(self.get_current_conditions(), indent=4, sort_keys=True)
        