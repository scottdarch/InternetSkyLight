import json

import requests


class WeatherUnderground(object):
    
    @classmethod
    def on_visit_argparse(cls, parser):
        parser.add_argument('--wukey', help="API key for the weather underground")
        return parser
    
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
    
    def __init__(self, args):
        self._key = args.wukey
    
    def get_current_conditions(self, city):
        r = requests.get("http://api.wunderground.com/api/{}/conditions/q/CA/{}.json".format(self._key, city))
        return r.json()
    
    def get_current_weather(self, city):
        return self.get_current_conditions(city)['current_observation']['weather']
    
    def print_complete_weather(self, city):
        print json.dumps(self.get_current_conditions(city), indent=4, sort_keys=True)
        