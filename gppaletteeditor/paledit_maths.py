from math import pi, cos, sin
import numpy as np

def angle_boundaries(R, r, angles, mti):
    nmt = len(angles)

    if mti > 0:
        low = angles[mti-1] + 2*r/R
    else:
        low = 0
    
    if mti < nmt-1:
        hgh = angles[mti+1] - 2*r/R
    else:
        hgh = 2*pi

    return low,hgh

def is_in_boundaries(R, r, angles, mti, a):
    nmt = len(angles)

    if mti > 0:
        lb = angles[mti-1] + 2*r/R
        low = (a > lb)
    else:
        low = (a > 0)
    
    if mti < nmt-1:
        hb = angles[mti+1] - 2*r/R
        hgh = (a < hb)
    else:
        hgh = a < 2*pi

    return hgh and low

def pol2cart(R=1., th=0.):
    return R*np.asarray([cos(th), sin(th)])