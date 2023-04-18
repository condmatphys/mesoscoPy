"""
functions for Hall bar characterisation
"""

from numpy import flip, pi
from scipy import constants

def symmetrise(array, axis=1, anti=False):
    ''' function to symmetrise an array along axis ```axis```.
    if ```anti=True```, then antisimmetrisation
    '''
    if anti:
        return (array - flip(array, axis=axis))/2
    else:
        return (array + flip(array, axis=axis))/2
    
    
def rhoxx(Rxx, W, L):
    return Rxx*W/L


def rhoxy(Rxy, W, L):
    return Rxy


def sigma(rhoxx, rhoxy):
    ''' function to calculate sigmaxx from rhoxx and rhoxy.
    to calculate sigmaxy, use rhoxy and rhoxx as inputs.
    '''
    return rhoxx/(rhoxx**2 + rhoxy**2)

def density(Rxy, B):
    '''input: Rxy measured at + and - B and antisymmetrised, B'''
    return B / constants.e / Rxy


def hall_mobility(sigma, n):
    '''return the Hall mobility from conductivity and density
    '''
    return [abs(sigma[i]/n[i]/constants.e) for i in range(len(sigma))]

def fet_mobility(V_gate, rho, k=3.9, d=None, Cg=None):
    if d != None and Cg !=None:
        raise KeyError
    elif d != None:
        Cg = k*constants.epsilon_0 / d
    else:
        pass
    
    return rho / V_gate / Cg

def meanfreepath(sigma, n):
    '''return the mean free path from conductivity and density
    '''
    return [constants.hbar * np.sqrt(abs(pi / n[i]))/e**2*sigma[i] for i in range(len(sigma))]