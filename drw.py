import blf, bpy
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *
import os

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
#ifdef __CUSTOM_ANGLES__
uniform float mat_thetas[__NMAT__];
#endif
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

bool in_interval(float x, float a, float b){
    return (x >= a) && (x <= b);
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

#ifdef __CUSTOM_ANGLES__
    int i = 0;
    if( mat_nb > 1 ){
        float alpha = 0.5*(mat_thetas[0] + mat_thetas[mat_nb-1]);
        // specific case of i = 0
        if ( (dt >= 0.5*(mat_thetas[0] + mat_thetas[1 % mat_nb])) 
                && ( ( alpha > PI ) || ( dt < alpha + PI ) ) 
                && ( ( alpha < PI ) || ( dt < alpha - PI ) )  ){
            // general case : i > 0 and i < mat_nb - 1
            i = 1;
            while( i < mat_nb - 1){
                if( in_interval( 2*dt-mat_thetas[i], mat_thetas[i-1], mat_thetas[i+1]) ){
                    break;
                }
                ++i;
            }    
        } // case i = mat_nb-1 is handled by default
    }
#else
    int i = int(floor((dt*mat_nb/PI + 1)/2));
    i = (i == mat_nb) ? 0 : i;
#endif

    /* get color and if circle is currently selected */
    vec4 fill_color = mat_fill_colors[i];
    vec4 line_color = mat_line_colors[i];
    bool is_selected = (i == mat_selected);
    bool is_active = (i == mat_active);
    
    /* compute the center of circle */
#ifdef __CUSTOM_ANGLES__
    float th_i = mat_thetas[i];
#else
    float th_i = 2*PI*i/mat_nb;
#endif
    float R = is_selected?(mat_centers_radius + selected_radius - mat_radius):mat_centers_radius;
    vec2 ci = R*vec2(cos(th_i),sin(th_i));
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
    
    # ifl = open("draw_icon.frag.glsl", 'r')
    # fsh = ifl.read()
    # ifl.close()
    fsh = main_circle_fsh

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

def load_gpu_texture(im_name):
    if not (im_name in bpy.data.images):
        return None

    im = bpy.data.images[im_name]
    gpu_tex = gpu.texture.from_image(im)
    if (gpu_tex.height > 1) or (gpu_tex.width > 1):
        return gpu_tex
        
    return None

def draw_centered_texture(settings, rds):
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
    gpmp = bpy.context.scene.gpmatpalette
    sid = settings.mat_selected
    if ( sid == settings.cached_mat_selected ) :
        tx = settings.cached_gpu_tex
    elif ( sid == -1 ) or ( not gpmp.materials[sid].image ):
        tx = load_gpu_texture(gpmp.image)
    else:
        tx = load_gpu_texture(gpmp.materials[sid].image) 
    
    shader, batch = setup_shader(settings,centered_tex_fsh)
    shader.uniform_sampler("tex",tx)
    shader.uniform_float("rad_tex",rds)    
    batch.draw(shader) 

    settings.cached_gpu_tex = tx
    settings.cached_mat_selected = sid

def draw_callback_px(op, context,settings): 
    gpu.state.blend_set('ALPHA')   
    
    draw_main_circle(settings)  
    if settings.useGPUTexture():
        draw_centered_texture(settings, settings.tex_radius)
    if settings.mat_selected >= 0:
        write_selected_mat_name(settings, settings.mat_selected)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    # op.check_time()
    