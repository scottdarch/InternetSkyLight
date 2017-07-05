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
import datetime
import time

import ephem


class HyperClock(object):
    '''
    Fake clock that ticks at a programmable rate for use in debugging or for
    just doing funky things with the light over time.
    '''
    
    @staticmethod
    def create_hyper_clock(args):
        return HyperClock(args)
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers):  # @UnusedVariable
        subparser = subparsers.add_parser("hypertime", help="Clock that can tick at an accelerated rate.")
        subparser.add_argument('--now-utc', type=str, default=str(ephem.now()), help='fake starting time')
        subparser.add_argument('--multiplier', '-m', type=int, default=6000, metavar="(X speed)")
        subparser.set_defaults(func=cls.create_hyper_clock)
    
    def __init__(self, args):
        self._hyper_now = ephem.date(args.now_utc)
        self._last_tick = time.time()
        self._multiplier = args.multiplier
        self._verbose = args.verbose
        if self._verbose:
            self._last_hour = ephem.date(self._hyper_now).tuple()[3]
            print "Using HyperClock ({} X).".format(self._multiplier)
    
    def now(self):
        real_now = time.time()
        elapsed = real_now - self._last_tick
        self._last_tick = real_now
        self._hyper_now += (elapsed * self._multiplier) / (60 * 60 * 24)
        if self._verbose:
            hour = ephem.date(self._hyper_now).tuple()[3]
            if self._last_hour != hour:
                self._last_hour = hour
            
        return self._hyper_now


class WallClock(object):
    '''
    Simple clock that uses the current system time.
    '''
    @staticmethod
    def create_wall_clock(args):
        return WallClock(args)
    
    @classmethod
    def on_visit_argparse(cls, parser, subparsers):  # @UnusedVariable
        subparser = subparsers.add_parser("realtime", help="Uses system time.")
        subparser.set_defaults(func=cls.create_wall_clock)
        
    def __init__(self, args):
        self._verbose = args.verbose
        if self._verbose:
            print "Using system time."

    def now(self):
        return ephem.now()
    