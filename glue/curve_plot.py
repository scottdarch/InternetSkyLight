#!/usr/bin/env python

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

def make_curve(morning_twilight, dawn, dusk, dark, noon=12.5):
    control_points = [
        [ morning_twilight, 0.00], 
        [ dawn            , 0.95], 
        [ noon            , 1.35], 
        [ dusk            , 0.95], 
        [ dark            , 0.00]
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
        xy=(t[ni], s[ni]), arrowprops=dict(arrowstyle='->'), xytext=(t[ni] - 5, s[ni] - .25))
        
        plt.xlabel('time (hour)')
        plt.ylabel('intensity')
        plt.gcf().axes[0].xaxis.set_major_formatter(MerkinFormatter())
        plt.xlim(0, 24)
        plt.title('daylight')
        plt.grid(False)
        plt.show()

def main():
    plot_curve(make_curve(6.5, 7, 19, 20.5), 7, 19)
    
if __name__ == "__main__":
    main()
