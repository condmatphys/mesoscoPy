"""
functions for usual conversions
"""

from numpy import log10, gradient, roll, cumsum
from time import strftime, gmtime


def Vrf2dBm(V, attenuation):
    ''' function to return a power value in dBm, from input voltage, in V
    '''
    return 20 * log10(V) + 13 + attenuation


def dBm2Vrf(dBm, attenuation):
    ''' function to return a voltage (in V) value, from power input in dBm
    '''
    return 10**((dBm - 13 - attenuation)/20)


def timestamp2fmt(timestamp, fmt='%d-%m-%Y %H:%M:%S'):
    return strftime(fmt, gmtime(timestamp))


def derivative(f, x, axis=None):
    ''' returns df(x)/dx
    '''
    dx = (x - roll(x, 1))[1:].mean()
    return gradient(f, dx, axis=axis)


def average(x, y, avgs, axis=None):

    xx = cumsum(x, dtype=float)
    xx[avgs:] = xx[avgs:] - xx[:-avgs]
    xx = xx[avgs - 1:] / avgs

    ret = cumsum(y, axis=axis, dtype=float)
    ret[avgs:] = ret[avgs:] - ret[:-avgs]
    return xx, ret[avgs - 1:] / avgs
