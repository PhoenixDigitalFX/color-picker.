# Useful functions for picker related interactions
from math import atan2, pi
import numpy as np
import bpy

''' Sets the given material as active '''
def pick_material(cache, context, settings, id_in_cache, brush_id):
    if (id_in_cache < 0) or (id_in_cache >= cache.mat_nb):
        return True
    
    obj = context.active_object    

    def set_active_brush(mat_id, brush_id):
        if brush_id < 0:
            return

        brush = cache.brushes[mat_id][brush_id]
        context.tool_settings.gpencil_paint.brush = brush

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

    bsh_id = brush_id
    if (brush_id < 0) and (settings.use_default_brushes):
        bsh_id = cache.bsh_default[id_in_cache]
    set_active_brush(id_in_cache, bsh_id)

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


''' Computes the ID of the material in selection according to the location of the mouse '''
def get_selected_brush_id(event, region_dim, origin, nbrush, interaction_radius, brush_radius):
    if nbrush < 1:
        return -1

    mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*region_dim
    mouse_local = mouse_pos - origin

    d_mouse = np.linalg.norm(mouse_local)
    
    if d_mouse < interaction_radius:
        return -1 

    if nbrush == 1:
        return 0    

    d_loc  = (d_mouse - interaction_radius)/(2*brush_radius)
    brush_id = int(d_loc)

    if brush_id > nbrush-1:
        brush_id = nbrush-1
    
    return brush_id
