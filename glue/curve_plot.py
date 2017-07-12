#!/usr/bin/env python

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
from matplotlib import ticker
from scipy.misc import comb  # @UnresolvedImport

import matplotlib.pyplot as plt
import numpy as np


def bezier(k, n, t):
    '''
    see https://pomax.github.io/bezierinfo/
    '''
    return comb(n,k) * (1-t)**(n-k) * t**(k)
  
def bezier_curve(control_points, nTimes):
    '''
    see https://pomax.github.io/bezierinfo/
    '''
    
    nPoints = len(control_points)
    xPoints = np.array([p[0] for p in control_points])
    yPoints = np.array([p[1] for p in control_points])

    t = np.linspace(0.0, 1.0, nTimes, True)

    polynomial_array = np.array([ bezier(i, nPoints-1, t) for i in range(0, nPoints) ])

    xvals = np.dot(xPoints, polynomial_array)
    yvals = np.dot(yPoints, polynomial_array)

    return xvals, yvals

class MerkinFormatter(ticker.Formatter):
    
    def __call__(self, x, pos=0):  # @UnusedVariable
        mhr = x % 12
        if mhr < 1:
            return "12"
        else:
            return "{:.0f}".format(mhr)

def make_curve(morning_twilight, dawn, dusk, dark):
    noon = dawn + ((dusk - dawn) / 2.0)
    control_points = [
        [ morning_twilight, 0.01], 
        [ dawn            , 1.80], 
        [ noon            , 0.30], 
        [ dusk            , 1.80], 
        [ dark            , 0.01]
        ]
                       
    return bezier_curve(control_points,
                        round((dark - morning_twilight) * 3600))

def plot_curve(xy, dawn=None, dusk=None):
    
    with plt.xkcd():
        t = xy[0]
        s = xy[1]
        
        if dawn is not None:
            plt.plot([dawn, dawn], [1.0, 0], linestyle="dashed", color="grey")
        if dusk is not None:
            plt.plot([dusk, dusk], [1.0, 0], linestyle="dashed", color="grey")
        
        plt.plot(t, s, color="blue")
        
        ni = int(len(t) / 2)
        plt.annotate(
        'FREE SANDWICHES',
        xy=(t[ni], s[ni]), arrowprops=dict(arrowstyle='->'), xytext=(t[ni], s[ni] - .5))
        
        plt.xlabel('time (day)')
        plt.ylabel('intensity')
        plt.title('daylight')
        plt.grid(False)
        plt.show()

def main():
    twi  = 0.000
    dawn = 0.025
    dusk = 0.750
    dark = 0.775
    xy = make_curve(twi, dawn, dusk, dark)
    print "{} - {}".format(xy[0][0], xy[0][-1])
    plot_curve(xy, dawn, dusk)
    
if __name__ == "__main__":
    main()
    