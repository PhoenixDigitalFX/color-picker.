from http import server
import bpy
import numpy as np
from math import *

bl_info = {
    "name": "GP Color Picker",
    "author": "Les Fées Spéciales (LFS)",
    "description": "Quickly switch between materials of the active Grease pencil object",
    "blender": (3, 0, 0),
    "version": (1,0,1),
    "location": "Press S in Draw mode with a GP object activated",
    "category": "00"
}

### ----------------- User Preferences
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *
import json, os
class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.4,0.4,0.4,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__
    crt_fpt = ''

    # TODO: add keymap in prefs    
    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=250, max=500
    )    

    def on_file_update(self, value):
        fpt = self.json_fpath
        if fpt == self.crt_fpt:
            return

        if not os.path.isfile(fpt):
            print("Error : {} path not found".format(fpt))
            return 

        fnm = os.path.basename(fpt)
        ext = fnm.split(os.extsep)
        
        if (len(ext) < 2) or (ext[-1] != "json"):
            print("Error : {} is not a json file".format(fnm))
            return 
        
        #TODO: fix this update that does not work
        self.crt_fpt = fpt
        
        ifl = open(fpt, 'r')
        ctn = json.load(ifl)
        ifl.close()

        print(ctn)

    theme: PointerProperty(type=GPCOLORPICKER_theme)
    json_fpath: StringProperty(
        subtype='FILE_PATH', name='File path', update=on_file_update, options={'TEXTEDIT_UPDATE'})

    mat_mode: EnumProperty(name="Material Mode", items=[("from_active", "From Active", 'Set Materials from active object'), ("from_file", "From File", 'Set Materials from JSON file')], \
                            default="from_file")

    def draw(self, context):
        layout = self.layout
        frow = layout.row()
        fcol = frow.column()
        stgs = fcol.box()
        stgs.label(text="Settings", icon='MODIFIER')
        stgs.prop(self, "icon_scale")

        props = fcol.box()
        props.label(text="Theme", icon='RESTRICT_COLOR_ON')
        props.prop(self.theme, 'pie_color', text="Pie Color")
        props.prop(self.theme, 'line_color', text="Line Color")
        props.prop(self.theme, 'text_color', text="Text Color")

        scol = frow.column()
        mats = scol.box()
        mats.label(text="Materials", icon='MATERIAL')
        mats.row().prop_tabs_enum(self, "mat_mode")

        if self.mat_mode == "from_file":
            mats.prop(self, "json_fpath")

        prv = scol.box()
        prv.label(text="Preview", icon='NONE')
    
class GPCOLORPICKER_MaterialSettings(PropertyGroup):
    is_picked: bpy.props.BoolProperty


### --------------- Settings
addon_keymaps = [] 
class GPCOLORPICKER_settings():
    def __init__(self): 
        self.key_shortcut = 'S'
        self.origin = np.asarray([0,0])
        self.active_obj = None
        self.materials = []
        self.region_dim = np.asarray([0,0])
        self.anti_aliasing_eps = 0.5

        self.set_icon_scale(250)
        self.mat_line_width = 5.
        self.mc_line_width = 1.

        self.mc_fill_color = (0.4,0.4,0.4,1.)
        self.mc_line_color = (0.96,0.96,0.96,1.)
        self.active_color =  (0.05,0.05,0.05,1)

        self.mat_nb = -1
        self.mat_selected =  -1
        self.mat_active =  -1
        self.mat_fill_colors = []
        self.mat_line_colors = []
        self.mat_tex = []

        self.text_color = (0.,0.,0.,1.)

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        self.mat_centers_radius = self.icon_scale/(2*(1.2))
        self.mc_outer_radius = 0.9*self.mat_centers_radius
        self.mc_inner_radius = 0.6*self.mc_outer_radius
        self.interaction_radius = 0.5*self.mc_outer_radius

        self.mat_rmin = 20
        self.mat_rmax = 0.2*self.mat_centers_radius
        self.mat_radius = self.mat_rmax

        self.selected_radius = 1.2*self.mat_radius
        self.mat_nmax = floor(pi/asin(self.mat_rmin/self.mat_centers_radius))
        self.text_size = ceil(0.08*self.icon_scale)

    def load_mat_radius(self):
        if self.mat_nb <= 1:
            return self.mat_rmax
        r_opt = 0.8*self.mat_centers_radius*sin(pi/self.mat_nb)
        self.mat_radius = max(self.mat_rmin,min(r_opt,self.mat_rmax))
        self.selected_radius = self.mat_radius*1.2
        return self.mat_radius

settings = GPCOLORPICKER_settings()

### --------------- GPU drawing
import blf
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *

vsh = '''            
        uniform mat4 modelViewProjectionMatrix;
        uniform float dimension;
        uniform vec2 origin;
        
        in vec2 pos;
        out vec2 lpos;
        out vec2 uv;

        void main()
        {
          gl_Position = modelViewProjectionMatrix*vec4(dimension*pos+origin, 0.0, 1.0);
          lpos = dimension*pos;
          uv = (pos+1)*0.5;
        }
    '''

def setup_vsh(settings,shader):
        # Simple screen quad
    dimension = settings.mat_centers_radius + 2*settings.mat_radius
    vdata = np.asarray(((-1, 1), (-1, -1),(1, -1), (1, 1)))
    vertices = np.ndarray.tolist(vdata)        
    indices = ((0, 1, 2), (0, 2, 3))
    
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind() 
    
        # Set up uniform variables
    matrix = gpu.matrix.get_projection_matrix()*gpu.matrix.get_model_view_matrix()
    shader.uniform_float("modelViewProjectionMatrix", matrix)     
    shader.uniform_float("dimension",dimension)
    shader.uniform_float("origin", settings.origin)
    return batch 

main_circle_fsh = '''
        #define PI 3.1415926538
        uniform vec4 circle_color;
        uniform vec4 line_color;
        uniform float inner_radius;
        uniform float outer_radius;
        uniform float line_width;
        uniform float selected_radius;
        uniform vec4 active_color;
        uniform float mat_radius;
        uniform float mat_line_width;
        uniform float mat_centers_radius;
        uniform int mat_nb;
        uniform int mat_selected;
        uniform int mat_active;
        uniform vec4 mat_fill_colors[__NMAT__];
        uniform vec4 mat_line_colors[__NMAT__];
         
        uniform float aa_eps;
        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;            
        
        float aa_circle(float rds, float dst, float eps){
            return smoothstep(rds+eps, rds-eps, dst);
        }        

        float aa_contour(float rds, float wdt, float dst, float eps){
            float a0 = aa_circle(rds+wdt/2., dst, eps);
            float a1 = aa_circle(rds-wdt/2., dst, eps);
            return a0*(1-a1);
        }     

        float aa_donut(float rds0, float rds1, float dst, float eps){
            float a0 = aa_circle(rds0, dst, eps);
            float a1 = aa_circle(rds1, dst, eps);
            return a0*(1-a1);
        }
        vec4 alpha_compose(vec4 A, vec4 B){
            /* A over B */
            vec4 color = vec4(0.);
            color.a = A.a + B.a*(1.- A.a);
            if( color.a == 0. ){
                return color;
            }
            color.rgb = (A.rgb * A.a + B.rgb * B.a * (1 - A.a))/(color.a);
            return color;
        }

        void main()
        {                    
          /*    MAIN CIRCLE    */
          float d = length(lpos);

          vec4 fill_color_ = circle_color;
          vec4 stroke_color = line_color;

          fill_color_.a *= aa_donut(outer_radius, inner_radius, d, aa_eps);
          stroke_color.a *= aa_contour(inner_radius, line_width, d, aa_eps);

          vec4 fragColor_main = alpha_compose(stroke_color, fill_color_);     

          /*    MATERIALS CIRCLES    */
           /* find optimal circle index for current location */
          vec2 loc_pos = lpos;
          float dt = mod(atan(loc_pos.y, loc_pos.x),2*PI);
          int i = int(floor((dt*mat_nb/PI + 1)/2));
          i = (i == mat_nb) ? 0 : i;

          /* get color and if circle is currently selected */
          vec4 fill_color = mat_fill_colors[i];
          vec4 line_color = mat_line_colors[i];
          bool is_selected = (i == mat_selected);
          bool is_active = (i == mat_active);
          
          /* compute the center of circle */
          float th_i = 2*PI*i/mat_nb;
          vec2 ci = mat_centers_radius*vec2(cos(th_i),sin(th_i));
          d = length(lpos-ci);     
                  
          /* draw circle */
          float radius = is_selected?selected_radius:mat_radius;
          fill_color.a *= aa_circle(radius, d, aa_eps);
          line_color.a *= aa_contour(radius, mat_line_width, d, aa_eps);

          vec4 fragColor_mat = alpha_compose(line_color, fill_color);

          if( is_active ){
              vec4 act_color = active_color;
              float act_rds = mat_centers_radius + mat_radius + mat_line_width*2;
              vec2 act_ctr = act_rds*vec2(cos(th_i),sin(th_i));
              float act_dst = length(lpos-act_ctr);
              act_color.a *= aa_circle(mat_line_width, act_dst, aa_eps);
              fragColor_mat = alpha_compose(act_color, fragColor_mat);
          }

          fragColor = alpha_compose(fragColor_mat, fragColor_main);           
        }
    '''

def draw_main_circle(settings):      
    nmat = settings.mat_nb
    if nmat <= 0:
        return    
    
    fsh = main_circle_fsh.replace("__NMAT__",str(nmat));
    shader = gpu.types.GPUShader(vsh, fsh)
    batch = setup_vsh(settings,shader)
    
    shader.uniform_float("circle_color", settings.mc_fill_color)
    shader.uniform_float("line_color", settings.mc_line_color)
    shader.uniform_float("inner_radius", settings.mc_inner_radius)
    shader.uniform_float("outer_radius", settings.mc_outer_radius)
    shader.uniform_float("line_width", settings.mc_line_width)

    shader.uniform_float("selected_radius", settings.selected_radius)
    shader.uniform_float("active_color", settings.active_color)
    shader.uniform_float("mat_radius", settings.mat_radius)
    shader.uniform_float("mat_line_width", settings.mat_line_width)
    shader.uniform_float("mat_centers_radius", settings.mat_centers_radius); 
    shader.uniform_int("mat_nb", settings.mat_nb);    
    shader.uniform_int("mat_selected", settings.mat_selected);   
    shader.uniform_int("mat_active", settings.mat_active);   

    def set_uniform_vector_float(shader, data, var_name):
        if(len(data) == 0):
            return
        dim = [len(data),len(data[0])]
        buf = gpu.types.Buffer('FLOAT', dim, data)
        loc = shader.uniform_from_name(var_name)
        shader.uniform_vector_float(loc, buf, dim[1], dim[0])

    set_uniform_vector_float(shader, settings.mat_fill_colors, "mat_fill_colors")
    set_uniform_vector_float(shader, settings.mat_line_colors, "mat_line_colors")

    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    batch.draw(shader)  


def draw_text(settings):
    def write_circle_centered(org, ird, text):
        font_id = 1
        blf.color(font_id, *(settings.text_color))
        blf.size(font_id, settings.text_size, 72)
        blf.enable(font_id,blf.CLIPPING)
        
        dmin, dmax = org - ird, org + ird
        blf.clipping(font_id, dmin[0], dmin[1], dmax[0], dmax[1])
        
        txd = np.asarray(blf.dimensions(font_id, text))
        pos = org - 0.5*txd
        blf.position(font_id, pos[0], pos[1], 0)
        blf.draw(font_id, text)
        gpu.state.blend_set('ALPHA')   

    # Material names when selected
    txt = settings.materials[settings.mat_selected].name
    org = settings.origin + 0.5*settings.region_dim
    ird = settings.mc_outer_radius
    write_circle_centered(org, ird, txt)

def draw_test(settings):
    test_fsh = '''
        #define PI 3.1415926538
        uniform sampler2D tex;  
        uniform float ratio;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;      

        void main()
        {                  

            fragColor = texture(tex,ratio*uv);

        }
    '''
    shader = gpu.types.GPUShader(vsh, test_fsh)
    batch = setup_vsh(settings,shader)

    tx = settings.mat_tex[settings.mat_selected]
    shader.uniform_sampler("tex",tx)
    shader.uniform_float("ratio",5)
    
    batch.draw(shader)  


def draw_callback_px(op, context,settings):    
    gpu.state.blend_set('ALPHA')   
    
    draw_main_circle(settings)  
    draw_text(settings)
    # if settings.mat_selected >= 0:
    #     draw_test(settings)

    # Reset blend mode
    gpu.state.blend_set('NONE')


    
### ----------------- Operator definition
class GPCOLORPICKER_OT_wheel(bpy.types.Operator):
    bl_idname = "object.gcp"
    bl_label = "GP Color Picker"    
    
    def __init__(self): pass            
    def __del__(self): pass

    @classmethod
    def poll(cls, context):
        return  (context.area.type == 'VIEW_3D') and \
                (context.mode == 'PAINT_GPENCIL') and \
                (context.active_object is not None) and \
                (context.active_object.type == 'GPENCIL')

    def get_selected_mat_id(self,event):
        # Find mouse position
        mouse_pos = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*settings.region_dim
        
        # Check in which section of the circle the mouse is located
        mouse_local = mouse_pos - settings.origin
        if np.linalg.norm(mouse_local) < settings.interaction_radius:
            return -1              
        dt = atan2(mouse_local[1], mouse_local[0]) % (2*pi)
        return int(floor((dt*settings.mat_nb/pi + 1)/2)) % (settings.mat_nb)

    def modal(self, context, event):
        context.area.tag_redraw()

        def validate_selection():
            i = settings.mat_selected
            if (i >= 0) and (i < settings.mat_nb):
                settings.active_obj.active_material_index = i
                settings.active_obj.active_material = settings.materials[i]   
                return True
            return False

        if event.type == 'MOUSEMOVE':
            settings.mat_selected = self.get_selected_mat_id(event)
        
        elif ((event.type == settings.key_shortcut) \
                and (event.value == 'RELEASE')):
            if validate_selection():       
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                return {'FINISHED'}
                
        elif (event.type == 'LEFTMOUSE'):
            validate_selection()          
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'FINISHED'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    def load_grease_pencil_materials(self):
        s = settings
        s.active_obj = bpy.context.active_object

        if s.active_obj is None:
            # Should be avoided by poll function but who knows
            self.report({'ERROR'}, "No active object")
            return False

        s.materials = [ m.material for k,m in s.active_obj.material_slots.items() \
                                    if m.material.is_grease_pencil ]       
        s.mat_nb = min(s.mat_nmax,len(s.materials))
        s.mat_active = s.active_obj.active_material_index

        if s.mat_nb == 0:
            self.report({'INFO'}, "No material in the active object")
            return False

        s.load_mat_radius()
        mat_gp = [ m.grease_pencil for m in s.materials ]
        s.mat_fill_colors = [ m.fill_color if m.show_fill else ([0.,0.,0.,0.]) for m in mat_gp ]
        s.mat_line_colors = [ m.color if m.show_stroke else ([0.,0.,0.,0.]) for m in mat_gp ] 
        
        return True

    def load_preferences(self, prefs):
        settings.set_icon_scale(prefs.icon_scale)
        settings.mc_fill_color = prefs.pie_color
        settings.mc_line_color = prefs.line_color
        settings.text_color = prefs.text_color

    def invoke(self, context, event):  
        # Update settings from user preferences
        prefs = context.preferences.addons[__name__].preferences
        if prefs is None : 
            self.report({'WARNING'}, "Could not load user preferences, running with default values")
        else:
            self.load_preferences(prefs)

        # Loading materials 
        if not (self.load_grease_pencil_materials()):
            return {'CANCELLED'}      

        # Setting modal handler
        self._handle = context.window_manager.modal_handler_add(self)
        if not self._handle:
            return {'CANCELLED'}  

        # Get mouse position
        region = bpy.context.region
        settings.region_dim = np.asarray([region.width,region.height])
        settings.origin = np.asarray([event.mouse_region_x,event.mouse_region_y]) - 0.5*settings.region_dim  
        self._handle = context.space_data.draw_handler_add(draw_callback_px, (self,context,settings), \
                                                        'WINDOW', 'POST_PIXEL')
        return {'RUNNING_MODAL'}    
        
def register():
    bpy.utils.register_class(GPCOLORPICKER_MaterialSettings)
    bpy.types.MaterialGPencilStyle.gcp_settings = bpy.props.PointerProperty(type=GPCOLORPICKER_MaterialSettings) 
    bpy.utils.register_class(GPCOLORPICKER_OT_wheel)
    bpy.utils.register_class(GPCOLORPICKER_theme)
    bpy.utils.register_class(GPCOLORPICKER_preferences)
    
    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, \
                                    type=settings.key_shortcut, value='PRESS')
        addon_keymaps.append((km, kmi))
    

def unregister():        
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(GPCOLORPICKER_theme)
    bpy.utils.unregister_class(GPCOLORPICKER_preferences)
    bpy.utils.unregister_class(GPCOLORPICKER_OT_wheel)
    bpy.utils.unregister_class(GPCOLORPICKER_MaterialSettings)
    
    
if __name__ == "__main__":
    register() 
