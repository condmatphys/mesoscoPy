"""
functions for usual conversions
"""

from numpy import log10


def Vrf2dBm(V, attenuation):
    ''' function to return a power value in dBm, from input voltage, in V
    '''
    return 20 * log10(V) + 13 + attenuation


def dBm2Vrf(dBm, attenuation):
    ''' function to return a voltage (in V) value, from power input in dBm
    '''
    return 10**((dBm - 13 - attenuation)/20)
