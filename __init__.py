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
    "location": "Press Ctrl+U in Draw mode with a GP object activated",
    # "warning": "In development",
    "category": "00"
}

### ----------------- User Preferences
from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import FloatVectorProperty, IntProperty

class GPCOLORPICKER_theme(PropertyGroup):
    pie_color: FloatVectorProperty(
        subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.4,0.4,0.4,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

class GPCOLORPICKER_preferences(AddonPreferences):
    bl_idname = __name__

    # TODO: add keymap in prefs    
    icon_scale: IntProperty(
        name="Icon scale",
        min=100, default=300, max=500
    )    
    pie_color: FloatVectorProperty(
            subtype='COLOR', name="Pie Color", min=0, max=1, size=4, default=(0.4,0.4,0.4,1.))
    line_color: FloatVectorProperty(
        subtype='COLOR', name="Line Color", min=0, max=1, size=4, default=(0.96,0.96,0.96,1.))
    text_color: FloatVectorProperty(
        subtype='COLOR', name="Text Color", min=0, max=1, size=4, default=(0.,0.,0.,1.))

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "icon_scale")
        layout.prop(self, "pie_color")
        layout.prop(self, "line_color")
        layout.prop(self, "text_color")

### --------------- Settings
addon_keymaps = [] 
class GPCOLORPICKER_settings():
    def __init__(self): 
        self.origin = np.asarray([0,0])
        self.active_obj = None
        self.materials = []
        self.region_dim = np.asarray([0,0])
        self.anti_aliasing_eps = 0.5

        self.set_icon_scale(300)
        self.mat_line_width = 2.
        self.mc_line_width = 1.

        self.mc_fill_color = (0.4,0.4,0.4,1.)
        self.mc_line_color = (0.96,0.96,0.96,1.)
        self.selected_color = (0.,1.,0.,1.)

        self.mat_nb = -1
        self.mat_selected =  -1
        self.mat_fill_colors = []
        self.mat_line_colors = []

        self.text_color = (0.,0.,0.,1.)

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        alpha = 0.9
        beta = 0.5
        gamma = 0.3
        self.mat_rmin = 20
        self.mat_centers_radius = self.icon_scale/(2*(1+gamma))
        self.mc_outer_radius = alpha*self.mat_centers_radius
        self.mc_inner_radius = beta*self.mc_outer_radius
        self.mat_rmax = gamma*self.mat_centers_radius
        self.mat_radius = self.mat_rmax
        self.mat_nmax = floor(pi/asin(self.mat_rmin/self.mat_centers_radius))
        self.text_size = ceil(0.08*self.icon_scale)

    def load_mat_radius(self):
        if self.mat_nb <= 1:
            return self.mat_rmax
        r_opt = 0.8*self.mat_centers_radius*sin(pi/self.mat_nb)
        self.mat_radius = max(self.mat_rmin,min(r_opt,self.mat_rmax))
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
        
        in vec2 pos;
        out vec2 uv;

        void main()
        {
          gl_Position = modelViewProjectionMatrix*vec4(pos, 0.0, 1.0);
          uv = pos;
        }
    '''

def setup_vsh(settings,shader):
        # Simple screen quad
    dimension = settings.mc_outer_radius + 2*settings.mat_radius
    vdata = dimension*(np.asarray(((-1, 1), (-1, -1),(1, -1), (1, 1))))+ settings.origin
    vertices = np.ndarray.tolist(vdata)        
    indices = ((0, 1, 2), (0, 2, 3))
    
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind() 
    
        # Set up uniform variables
    matrix = gpu.matrix.get_projection_matrix()*gpu.matrix.get_model_view_matrix()
    shader.uniform_float("modelViewProjectionMatrix", matrix)     
    return batch 

main_circle_fsh = '''
        #define PI 3.1415926538
        uniform vec4 circle_color;
        uniform vec4 line_color;
        uniform float inner_radius;
        uniform float outer_radius;
        uniform float line_width;       
        
        uniform vec2 origin;        
        uniform float aa_eps;
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
          float d = length(uv-origin);

          vec4 fill_color = circle_color;
          vec4 line_color_ = line_color;

          fill_color.a = aa_donut(outer_radius, inner_radius, d, aa_eps);
          line_color_.a = aa_contour(inner_radius, line_width, d, aa_eps);

          fragColor = alpha_compose(line_color_, fill_color);      
        }
    '''

def draw_main_circle(settings):      
    shader = gpu.types.GPUShader(vsh, main_circle_fsh)
    batch = setup_vsh(settings,shader)
    
    shader.uniform_float("circle_color", settings.mc_fill_color)
    shader.uniform_float("line_color", settings.mc_line_color)
    shader.uniform_float("inner_radius", settings.mc_inner_radius)
    shader.uniform_float("outer_radius", settings.mc_outer_radius)
    shader.uniform_float("line_width", settings.mc_line_width)

    shader.uniform_float("origin", settings.origin)
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    batch.draw(shader)  

mats_circle_fsh = '''
        #define PI 3.1415926538        
        uniform vec4 selected_color;
        uniform float mat_radius;
        uniform float mat_line_width;
        uniform float mat_centers_radius;
        uniform int mat_nb;
        uniform int mat_selected;
        uniform vec4 mat_fill_colors[__NMAT__];
        uniform vec4 mat_line_colors[__NMAT__];

        uniform vec2 origin;        
        uniform float aa_eps;
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
          /* find optimal circle index for current location */
          vec2 loc_uv = uv-origin;
          float dt = mod(atan(loc_uv.y, loc_uv.x),2*PI);
          int i = int(floor((dt*mat_nb/PI + 1)/2));
          i = (i == mat_nb) ? 0 : i;

          /* get color and if circle is currently selected */
          vec4 fill_color = mat_fill_colors[i];
          vec4 line_color = mat_line_colors[i];
          bool is_selected = (i == int(mat_selected));
          
          /* compute the center of circle */
          float th_i = 2*PI*i/mat_nb;
          vec2 ci = mat_centers_radius*vec2(cos(th_i),sin(th_i)) + origin;
          float d = length(uv-ci);     
                  
          /* check if inside circle */
          fill_color.a = aa_circle(mat_radius, d, aa_eps);
          line_color.a = aa_contour(mat_radius, mat_line_width, d, aa_eps);
          fragColor = alpha_compose(line_color, fill_color);

          if( is_selected ){
              float s_radius = mat_radius + mat_line_width*2;
              vec4 selection_color = selected_color;
              selection_color.a = aa_contour(s_radius, mat_line_width, d, aa_eps);
              fragColor = alpha_compose(selection_color, fragColor);
          }
        }
    '''

def set_uniform_vector_float(shader, data, var_name):
    if(len(data) == 0):
        return
    dim = [len(data),len(data[0])]
    buf = gpu.types.Buffer('FLOAT', dim, data)
    loc = shader.uniform_from_name(var_name)
    shader.uniform_vector_float(loc, buf, dim[1], dim[0])

def draw_material_circles(settings): 
    nmat = settings.mat_nb
    if nmat <= 0:
        return    
    
    fsh = mats_circle_fsh.replace("__NMAT__",str(nmat));
    shader = gpu.types.GPUShader(vsh, fsh)
    batch = setup_vsh(settings,shader)
    
    shader.uniform_float("selected_color", settings.selected_color)
    shader.uniform_float("mat_radius", settings.mat_radius)
    shader.uniform_float("mat_line_width", settings.mat_line_width)
    shader.uniform_float("mat_centers_radius", settings.mat_centers_radius); 
    shader.uniform_int("mat_nb", settings.mat_nb);    
    shader.uniform_int("mat_selected", settings.mat_selected);   

    set_uniform_vector_float(shader, settings.mat_fill_colors, "mat_fill_colors")
    set_uniform_vector_float(shader, settings.mat_line_colors, "mat_line_colors")

    shader.uniform_float("origin", settings.origin)
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    batch.draw(shader)   

def write_material_name(settings,mat_id):
    if mat_id < 0:
        return  
    text = settings.materials[mat_id].name
    font_id = 1
    blf.color(font_id, *(settings.text_color))
    blf.size(font_id, settings.text_size, 72)
    blf.enable(font_id,blf.CLIPPING)
    
    org = settings.origin + 0.5*settings.region_dim
    ird = settings.mc_outer_radius
    dmin, dmax = org - ird, org + ird
    blf.clipping(font_id, dmin[0], dmin[1], dmax[0], dmax[1])
    
    txd = np.asarray(blf.dimensions(font_id, text))
    pos = org - 0.5*txd
    blf.position(font_id, pos[0], pos[1], 0)
    
    blf.draw(font_id, text)
    gpu.state.blend_set('ALPHA')   

test_fsh = '''
        #define PI 3.1415926538
        uniform vec2 origin;
        uniform float radius; 
        uniform float width;      
        uniform float eps;
        //uniform sampler2D prev_tex;  
        in vec2 uv;
        out vec4 fragColor;      

        float simple_step(float rds, float dst){
            if(eps < 0){
                return 0.;
            }
            return (dst <= rds)?1.:0.;
        } 
        float smooth_step(float rds, float dst, float eps){
            return smoothstep(rds+eps, rds-eps, dst);
        }
        float gaussian_step(float rds, float dst, float eps){
            float o = rds-eps;
            if (dst < o){
                return 1.;
            }
            return exp( -(dst-o)*(dst-o)/(eps*eps) );          
        }
        float aa_circle(float rds, float dst){
            //return simple_step(rds,dst);
            return smooth_step(rds,dst,eps);
            //return gaussian_step(rds,dst,eps);
        }        
        float aa_contour(float rds, float dst, float wdt){
            float a0 = aa_circle(rds+wdt/2., dst);
            float a1 = aa_circle(rds-wdt/2., dst);
            return a0*(1-a1);
        }     
        vec4 alpha_compose(vec4 A, vec4 B){
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
          float d = length(uv-origin);

          vec3 fill_color = vec3(0,0.,1);
          float a_fill = aa_circle(radius, d);
          vec4 fill_fc = vec4(fill_color, a_fill);

          vec3 line_color = vec3(0,1,0);
          float a_line = aa_contour(radius, d, width);
          vec4 line_fc = vec4(line_color,a_line);

          fragColor = alpha_compose(line_fc, fill_fc);
        }
    '''

def draw_test(settings):
    shader = gpu.types.GPUShader(vsh, test_fsh)
    batch = setup_vsh(settings,shader)

    # import imbuf
    # im_path = __path__[0] + "/blender-icon.png"
    # im_buffer = imbuf.load(im_path)
    # im_tex = gpu.texture.from_image(im_buffer)
    
    eps = 1
    rds = settings.mc_outer_radius
    wdt = 2

    print(f'radius {rds}, eps = {eps}')

    shader.uniform_float("origin", settings.origin)
    shader.uniform_float("radius", rds)
    shader.uniform_float("width", wdt)
    shader.uniform_float("eps", eps)
    
    batch.draw(shader)  


def draw_callback_px(op, context,settings):    
    gpu.state.blend_set('ALPHA')   
    
    draw_main_circle(settings)  
    draw_material_circles(settings)  
    write_material_name(settings,settings.mat_selected)
    # if settings.mat_selected >= 0:
    # draw_test(settings)

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
        if np.linalg.norm(mouse_local) < settings.mc_inner_radius:
            return -1              
        dt = atan2(mouse_local[1], mouse_local[0]) % (2*pi)
        return int(floor((dt*settings.mat_nb/pi + 1)/2)) % (settings.mat_nb)

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            settings.mat_selected = self.get_selected_mat_id(event)

        elif event.type == 'LEFTMOUSE':
            i = settings.mat_selected
            if (i >= 0) and (i < settings.mat_nb):
                settings.active_obj.active_material_index = i
                settings.active_obj.active_material = settings.materials[i]
            
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

        if s.mat_nb == 0:
            self.report({'INFO'}, "No material in the active object")
            return False

        s.load_mat_radius()
        s.mat_fill_colors = [ m.grease_pencil.fill_color for m in s.materials ]
        s.mat_line_colors = [ m.grease_pencil.color for m in s.materials ] 
        # mprv = [ m.preview for m in settings["materials"] ];
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
    bpy.utils.register_class(GPCOLORPICKER_OT_wheel)
    bpy.utils.register_class(GPCOLORPICKER_preferences)
    
    # Add the hotkey
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
        kmi = km.keymap_items.new(GPCOLORPICKER_OT_wheel.bl_idname, \
                                    type='U', value='PRESS', ctrl=True)
        addon_keymaps.append((km, kmi))
    

def unregister():        
    # Remove the hotkey
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    bpy.utils.unregister_class(GPCOLORPICKER_preferences)
    bpy.utils.unregister_class(GPCOLORPICKER_OT_wheel)
    
    
if __name__ == "__main__":
    register() 
