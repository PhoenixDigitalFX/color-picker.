# Useful functions for picker related interactions
from math import atan2, pi
import numpy as np
import bpy
from . picker_draw import load_gpu_texture

''' Sets the given material as active '''
def pick_material(cache, context, settings, id_in_cache):
    if (id_in_cache < 0) or (id_in_cache >= cache.mat_nb):
        return True
    
    obj = context.active_object    

    def set_active_material(id_in_obj):
        obj.active_material_index = id_in_obj

        if not cache.from_palette:
            return True
        
        gpmp = context.scene.gpmatpalettes.active()
        gpmt = gpmp.materials[id_in_cache]
        if not gpmt.layer:
            return True

        if not gpmt.layer in obj.data.layers:
            bpy.ops.gpencil.layer_add()
            obj.data.layers.active.info = gpmt.layer
        else:
            obj.data.layers.active = obj.data.layers[gpmt.layer]

        return True

    if not cache.from_palette:
        return set_active_material(id_in_cache)
    
    ob_mat = obj.data.materials                
    mat = cache.materials[id_in_cache]
    id_in_obj = ob_mat.find(mat.name)

    if id_in_obj >= 0:
        # Found material in current object
        return set_active_material(id_in_obj)
    
    if settings.mat_assign:
        # Assigning new material to current object
        id_in_obj = len(ob_mat)
        ob_mat.append(mat)
        return set_active_material(id_in_obj)

    return False

''' Computes the ID of the material in selection according to the location of the mouse '''
def get_selected_mat_id(event, region_dim, origin, nmt, interaction_radius, mat_angles):
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

    # specific case of i = 0
    alpha = 0.5*(mat_angles[0] + mat_angles[nmt-1]-2*pi)        
    if (alpha < 0):
        alpha += 2*pi

    beta = 0.5*(mat_angles[0] + mat_angles[1])

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
        beta = 2*dt-mat_angles[i]
        if( (beta >= mat_angles[i-1]) and (beta <= mat_angles[i+1])):
            return i
        i += 1
    # case i = mat_nb-1 is handled by default
    return nmt-1
        
''' Cache structure for better performances in displaying the picker 
    Mirrors the content of the active palette or the materials of the active object
'''
class CachedData:
    def __init__(self, context, from_palette=True):
        self.from_palette = from_palette
        self.refresh(context)        

    def refresh(self, context):
        ob = context.active_object   
        gpmp = context.scene.gpmatpalettes.active()

        if gpmp and self.from_palette:
            self.gpu_texture = load_gpu_texture(gpmp.image)
            self.pal_active = gpmp.name 
            self.mat_cached = -1

            self.materials = [ bpy.data.materials[n.name] for n in gpmp.materials ]       
            self.mat_nb = len(self.materials)
            
            if ob and ob.active_material and (ob.active_material.name in gpmp.materials):
                self.mat_active = list(gpmp.materials.keys()).index(ob.active_material.name)
            else:        
                self.mat_active = -1

            self.angles = [ m.get_angle() for m in gpmp.materials ]
            self.is_custom_angle = [ not m.is_angle_movable for m in gpmp.materials ]
            self.pick_origins = [ np.asarray(m.get_origin(True))\
                                    for m in gpmp.materials]                                            
        elif ob and not self.from_palette:
            self.gpu_texture = None
            self.pal_active = -1
            self.mat_cached = -1
    
            self.materials = [ m.material for k,m in ob.material_slots.items() \
                                        if (m.material) and (m.material.is_grease_pencil) ]       
            self.mat_nb = len(self.materials)
            self.mat_active = ob.active_material_index
            self.angles = np.linspace(0,2*pi,self.mat_nb+1)[:-1]  
            self.pick_origins= self.mat_nb*[np.asarray([0,0,0])]
        else:
            # Empty cache
            self.gpu_texture = None
            self.pal_active = -1
            self.mat_cached = -1

            self.materials = [ ]       
            self.mat_nb = len(self.materials)
            self.mat_active = -1
            self.angles = []
            self.pick_origins= []

        mat_gp = [ m.grease_pencil for m in self.materials ]
        transp = [0.,0.,0.,0.]
        self.mat_fill_colors = [ m.fill_color if m.show_fill else transp for m in mat_gp ]
        self.mat_line_colors = [ m.color if m.show_stroke else transp for m in mat_gp ] 

    def use_gpu_texture(self):
        return self.from_palette and not (self.gpu_texture is None)
