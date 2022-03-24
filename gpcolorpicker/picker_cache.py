from math import pi
import numpy as np
from . picker_draw import load_gpu_texture

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
            self.brushes = [ [b.data for b in m.brushes] for m in gpmp.materials ]
            self.brushes_pos = [ [float(i) for i,_ in enumerate(m.brushes)] for m in gpmp.materials ]

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
        all_brushes = { brush for mat_brushes in self.brushes for brush in mat_brushes } 
        self.bsh_prv = { b.name:getGPUPreviewTexture(b, check_custom=True) for b in all_brushes }

    def use_gpu_texture(self):
        return self.from_palette and not (self.gpu_texture is None)

    def get_picklines(self):
        return [ [ o[0], o[1], i ] for i,origins in enumerate(self.pick_origins) for o in origins  ]
