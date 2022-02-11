import blf
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *

def setup_shader(settings,fragsh):
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
    shader = gpu.types.GPUShader(vsh, fragsh)

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
    return shader,batch 


def draw_main_circle(settings):     
    nmat = settings.mat_nb
    if nmat <= 0:
        return    
    
    ifl = open("./draw_icon.frag.glsl", 'r')
    fsh = ifl.read()
    ifl.close()

    if settings.useCustomAngles() :
        csta_macro = "__CUSTOM_ANGLES__"
        fsh = "#define " + csta_macro + "\n" + fsh        

    fsh = fsh.replace("__NMAT__",str(nmat))

    shader, batch = setup_shader(settings,fsh)
    
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
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    def set_uniform_vector_float(shader, data_, var_name):
        if(len(data_) == 0):
            return
        data = data_
        if isinstance(data[0],float):
            data = [ [x] for x in data_ ]
        dim = [len(data),len(data[0])]
        buf = gpu.types.Buffer('FLOAT', dim, data)
        loc = shader.uniform_from_name(var_name)
        shader.uniform_vector_float(loc, buf, dim[1], dim[0])

    set_uniform_vector_float(shader, settings.mat_fill_colors, "mat_fill_colors")
    set_uniform_vector_float(shader, settings.mat_line_colors, "mat_line_colors")
    if settings.useCustomAngles():
        set_uniform_vector_float(shader, settings.custom_angles, "mat_thetas")  

    batch.draw(shader)  

def write_selected_mat_name(settings, id_selected):
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

    txt = settings.materials[id_selected].name
    org = settings.origin + 0.5*settings.region_dim
    ird = settings.mc_outer_radius
    write_circle_centered(org, ird, txt)

def draw_centered_texture(settings, tx, rds):
    centered_tex_fsh = '''
        #define PI 3.1415926538
        uniform sampler2D tex;  
        uniform float rad_tex;
        uniform float dimension;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;      

        void main()
        {          
            float aspect_ratio = textureSize(tex,0).x / float(textureSize(tex,0).y);
            float dim_ratio = dimension/rad_tex;
            vec2 uv_tex = dim_ratio * uv + 0.5*(1 - dim_ratio);
            uv_tex.y *= aspect_ratio;

            if((uv_tex.x < 0) || (uv_tex.x > 1) ||  (uv_tex.y < 0) || (uv_tex.y > 1)){
                fragColor = vec4(0.);
            }
            else{
                fragColor = texture(tex,uv_tex);
            }  
        }
    '''
    shader, batch = setup_shader(settings,centered_tex_fsh)
    shader.uniform_sampler("tex",tx)
    shader.uniform_float("rad_tex",rds)    
    batch.draw(shader) 

def draw_callback_px(op, context,settings):    
    gpu.state.blend_set('ALPHA')   
    
    draw_main_circle(settings)  
    if settings.mat_selected >= 0:
        write_selected_mat_name(settings, settings.mat_selected)
    if settings.useGPUTexture():
        draw_centered_texture(settings, settings.gpu_tex, settings.tex_radius)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    