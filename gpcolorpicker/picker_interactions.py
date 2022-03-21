# Useful functions for picker related interactions
from math import atan2, pi, sin, cos
import numpy as np
import bpy
from . picker_draw import load_gpu_texture

''' Sets the given material as active '''
def pick_material(cache, context, settings, id_in_cache, brush_id):
    if (id_in_cache < 0) or (id_in_cache >= cache.mat_nb):
        return True
    
    obj = context.active_object    

    def set_active_brush(mat_id, brush_id):
        if brush_id < 0:
            return
        bname = cache.map_bsh[mat_id][brush_id]
        brush = bpy.data.brushes[bname]
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
            bpy.ops.gapencil.layer_add()
            obj.data.layers.active.info = gpmt.layer
        else:
            obj.data.layers.active = obj.data.layers[gpmt.layer]

        return True

    set_active_brush(id_in_cache, brush_id)

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
            gpmp.compatibility_check()
            # From palette cache
            self.gpu_texture = load_gpu_texture(gpmp.image)
            self.pal_active = gpmp.name 
            self.mat_cached = -1

            self.materials = [ n.data for n in gpmp.materials ]       
            self.mat_nb = len(self.materials)
            
            if ob and ob.active_material:
                self.mat_active = gpmp.index_material(ob.active_material.name)
            else:        
                self.mat_active = -1

            self.angles = [ m.get_angle() for m in gpmp.materials ]
            self.is_custom_angle = [ not m.is_angle_movable for m in gpmp.materials ]
            self.pick_origins = [ m.get_origins() for m in gpmp.materials ]      

            self.brushes = gpmp.get_brushes()
            self.map_bsh = [ list(m.get_brushes_names()) for m in gpmp.materials]

        elif ob and not self.from_palette:
            # From active cache
            self.gpu_texture = None
            self.pal_active = -1
            self.mat_cached = -1
    
            self.materials = [ m.material for k,m in ob.material_slots.items() \
                                        if (m.material) and (m.material.is_grease_pencil) ]       
            self.mat_nb = len(self.materials)
            self.mat_active = ob.active_material_index
            self.angles = np.linspace(0,2*pi,self.mat_nb+1)[:-1]  
            self.pick_origins= self.mat_nb*[[]]  
            
            self.brushes = []
            self.map_bsh = []
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
            self.brushes = []
            self.map_bsh = []

        mat_gp = [ m.grease_pencil for m in self.materials ]
        transp = [0.,0.,0.,0.]
        self.mat_fill_colors = [ m.fill_color if m.show_fill else transp for m in mat_gp ]
        self.mat_line_colors = [ m.color if m.show_stroke else transp for m in mat_gp ] 

        def getGPUPreviewTexture(item, check_custom=False, use_icon=False):
            prv = item.preview
            if check_custom and (not item.use_custom_icon):
                return None
            elif not prv:
                item.asset_generate_preview()
                print(f"ERROR : Item {item.name} has no preview image")
                return None

            if use_icon:
                s = prv.icon_size
                dat = prv.icon_pixels_float
            else:
                s = prv.image_size
                dat = prv.image_pixels_float

            # data as a list : accelerates by far the buffer loading
            dat = [ d for d in dat ] 
            ts = s[0]*s[1]*4
            if ts < 1:
                item.asset_generate_preview()
                print(f"ERROR : Could not load mat {item.name} preview image")
                return None

            import gpu
            pbf = gpu.types.Buffer('FLOAT', ts, dat)
            return gpu.types.GPUTexture(s, data=pbf, format='RGBA16F')

        self.mat_prv = [ getGPUPreviewTexture(m) for m in self.materials ]
        self.bsh_prv = { b.name:getGPUPreviewTexture(b, check_custom=True) for b in self.brushes }

    def use_gpu_texture(self):
        return self.from_palette and not (self.gpu_texture is None)

    def get_picklines(self):
        return [ [ o[0], o[1], i ] for i,origins in enumerate(self.pick_origins) for o in origins  ]
