#!/usr/bin/env python

from matplotlib import ticker
from scipy.misc import comb

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

def plot_curve(morning_twilight, dawn, noon, dusk, dark):
    control_points = [
        [ morning_twilight, 0.00], 
        [ dawn            , 0.95], 
        [ noon            , 1.25], 
        [ dusk            , 0.95], 
        [ dark            , 0.00]
        ]
                       
    xy = bezier_curve(control_points,
                      round((dark - morning_twilight) * 3600))
    with plt.xkcd():
        t = xy[0]
        s = xy[1]
        
        plt.plot([dawn, dawn], [1.0, 0], linestyle="dashed", color="grey")
        plt.plot([dusk, dusk], [1.0, 0], linestyle="dashed", color="grey")
        
        plt.plot(t, s, color="blue")
        
        dai = int(((dawn - morning_twilight) / (dark - morning_twilight)) * len(t))
        plt.annotate(
        'DAWN',
        xy=(t[dai], s[dai]), arrowprops=dict(arrowstyle='->'), xytext=(t[dai] - 4, s[dai] + .25))
        
        dui = int((dusk - morning_twilight) * 3600.00)
        plt.annotate(
        'DUSK',
        xy=(t[dui], s[dui]), arrowprops=dict(arrowstyle='->'), xytext=(t[dui] + 4, s[dui] + .25))
        
        ni = int(len(t) / 2)
        plt.annotate(
        'FREE SANDWICHES',
        xy=(t[ni], s[ni]), arrowprops=dict(arrowstyle='->'), xytext=(t[ni] + 1, s[ni] + .25))
        
        for i in range(0, len(control_points)):
            plt.plot(control_points[i][0], control_points[i][1], marker='o', color='orange')
        
        plt.xlabel('time (hour)')
        plt.ylabel('intensity')
        plt.gcf().axes[0].xaxis.set_major_formatter(MerkinFormatter())
        plt.xlim(0, 24)
        plt.title('daylight')
        plt.grid(False)
        plt.show()

def main():
    plot_curve(6.5, 7, 12.5, 19, 20.5)
    
if __name__ == "__main__":
    main()
