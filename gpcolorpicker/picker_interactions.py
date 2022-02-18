from math import atan2, floor, pi
import numpy as np

def get_selected_mat_id(event, region_dim, origin, nmt, interaction_radius, custom_angles = []):
    if nmt < 1:
        return -1

    # Find mouse position
    mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*region_dim
    mouse_local = mouse_pos - origin
    
    # Check in which section of the circle the mouse is located
    if np.linalg.norm(mouse_local) < interaction_radius:
        return -1 
    
    if nmt == 1:
        return 0    

    dt = atan2(mouse_local[1], mouse_local[0]) % (2*pi)
    if len(custom_angles) == 0:
        return int(floor((dt*nmt/pi + 1)/2)) % (nmt)
        
    # Custom angles
    th = custom_angles

    # specific case of i = 0
    alpha = 0.5*(th[0] + th[nmt-1]-2*pi)        
    if (alpha < 0):
        alpha += 2*pi

    beta = 0.5*(th[0] + th[1])

    dt_pos = dt
    if (dt_pos < 0):
        dt_pos += 2*pi    

    if (alpha < beta):
        if (dt_pos >= alpha) and (dt_pos <= beta):
            return 0
    elif (dt_pos <= beta) or (dt_pos >= alpha):
        return 0

    # general case : i > 0 and i < mat_nb - 1
    i = 1
    while( i < nmt - 1 ):
        beta = 2*dt-th[i]
        if( (beta >= th[i-1]) and (beta <= th[i+1])):
            return i
        i += 1
    # case i = mat_nb-1 is handled by default
    return nmt-1