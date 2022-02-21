from math import atan2, floor, pi
import numpy as np
import bpy
from . picker_draw import load_gpu_texture


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
        
class CachedData:
    def __init__(self, from_palette=True):
        self.from_palette = from_palette
        self.refresh()        

    def refresh(self):
        ob = bpy.context.active_object      
        self.custom_angles = []  

        if self.from_palette:
            gpmp = bpy.context.scene.gpmatpalettes.active()
            self.gpu_texture = load_gpu_texture(gpmp.image)
            self.pal_active = gpmp.name 
            self.mat_cached = -1

            self.materials = [ bpy.data.materials[n.name] for n in gpmp.materials ]       
            self.mat_nb = len(self.materials)

            nmact = ob.active_material.name   
            if nmact in gpmp.materials:
                self.mat_active = list(gpmp.materials.keys()).index(nmact)
            else:        
                self.mat_active = -1

            if gpmp.hasCustomAngles():
                self.custom_angles = [ m.custom_angle for m in gpmp.materials ]
        else:
            self.gpu_texture = None
            self.pal_active = -1
            self.mat_cached = -1
    
            self.materials = [ m.material for k,m in ob.material_slots.items() \
                                        if (m.material) and (m.material.is_grease_pencil) ]       
            self.mat_nb = len(self.materials)
            self.mat_active = ob.active_material_index

        mat_gp = [ m.grease_pencil for m in self.materials ]
        transp = [0.,0.,0.,0.]
        self.mat_fill_colors = [ m.fill_color if m.show_fill else transp for m in mat_gp ]
        self.mat_line_colors = [ m.color if m.show_stroke else transp for m in mat_gp ] 
        
    def use_gpu_texture(self):
        return self.from_palette and self.gpu_texture

    def use_custom_angles(self):
        return self.from_palette and self.custom_angles