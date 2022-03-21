# GPU drawing related functions
import blf, gpu
from gpu_extras.batch import batch_for_shader
import numpy as np

''' Common GLSL functions used in many shaders 
    Mostly creates geometric primitives with anti-aliasing
'''
common_libsh='''
    vec4 srgb_to_linear_rgb(vec4 c){
        vec4 sc = c;
        sc.r = (c.r < 0.04045)?(c.r/12.92):( pow( (c.r+0.055)/1.055, 2.4) );
        sc.g = (c.r < 0.04045)?(c.g/12.92):( pow( (c.g+0.055)/1.055, 2.4) );
        sc.b = (c.r < 0.04045)?(c.b/12.92):( pow( (c.b+0.055)/1.055, 2.4) );
        return sc;
    }

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

    float aa_seg( vec2 s0, vec2 s1, vec2 p, float wdt, float eps){
        float lgt = length(s0-s1);
        vec2 udr = (s1-s0)/lgt;
        vec2 lp = p - s0;
        float prj = dot(lp, udr);
        float alpha = 1.;

        alpha *= smoothstep(-eps, eps, prj);  
        alpha *= smoothstep(lgt+eps, lgt-eps, prj);  
        if( alpha == 0.){
            return 0.;
        }
        
        float d = length(prj*udr - lp);
        return alpha*smoothstep(wdt+eps, wdt-eps, d);
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
'''

''' Useful function to set an array of float-based types* as shader uniform 
    *either float, vec2, vec3 or vec4
'''
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

''' Useful function to load an image data as GPU texture to be used in a shader'''
def load_gpu_texture(image):
    if not image:
        return None 

    gpu_tex = gpu.texture.from_image(image)
    if (gpu_tex.height > 1) or (gpu_tex.width > 1):
        return gpu_tex
        
    return None

''' Useful function to draw a single mark with common shape '''
def draw_mark(op, settings, m_origin, m_radius, m_color, m_type=0):
    mark_fsh = '''
    #define PI 3.1415926538
    uniform vec2 mark_origin;
    uniform vec4 mark_color;
    uniform float mark_radius;
    uniform float aa_eps;
    uniform int mark_type;

    in vec2 lpos;
    in vec2 uv;
    out vec4 fragColor;   

    vec4 draw_circle_mark(){
        float d = length(lpos-mark_origin); 
        vec4 fragColor_circle= mark_color;
        fragColor_circle.a *= aa_circle(mark_radius, d, aa_eps); 
        return fragColor_circle;
    }

    vec4 draw_cross_mark(){
        vec2 uv = abs(lpos-mark_origin);
        float l = 0.1*mark_radius;
        if(((uv.x < l) && (uv.y < mark_radius)) 
                || ((uv.y < l) && (uv.x < mark_radius))){
            return mark_color;
        }
        return vec4(0.);
    }

    vec4 draw_pencil_mark(){
        vec2 uv = lpos-mark_origin;
        // rotation
        float th = -3*PI/4.;
        float cs = cos(th);
        float sn = sin(th);
        uv = vec2( cs*uv.x - sn*uv.y , sn*uv.x + cs*uv.y );

        vec4 col= mark_color;

        float r = mark_radius;
        float l = 0.3*r;
        float alpha = 0.;

        alpha += aa_seg( vec2(-r, 0), vec2(l, 0), uv, l, aa_eps );
        alpha += aa_seg( vec2(r, 0), vec2(l, l*0.9), uv, l*0.1, aa_eps );
        alpha += aa_seg( vec2(r, 0), vec2(l, -l*0.9), uv, l*0.1, aa_eps );   

        col.a *= clamp(alpha, 0, 1);

        return col;
    }

    void main()
    {                    
        if(mark_type == 0){
            fragColor = draw_circle_mark();
        }
        else if(mark_type == 1){
            fragColor = draw_cross_mark();
        }
        else if(mark_type == 2){
            fragColor = draw_pencil_mark();
        }
        else{
            fragColor = vec4(0.);
        }
    }
    '''
    shader, batch = setup_shader(op, settings, mark_fsh)

    shader.uniform_float("mark_origin", m_origin) 
    shader.uniform_float("mark_radius", m_radius) 
    shader.uniform_float("mark_color", m_color) 
    shader.uniform_int("mark_type", m_type) 
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps) 

    batch.draw(shader)  

''' Useful function to display a texture
    op : operator to be drawn
    settings: operator's settings
    tx : texture to display
    center : central position of the texture drawing
    rds : dimension of the texture drawing
    use_mask : whether to use a disk mask around the texture
    convert_rgb : whether the texture needs to be converted from srgb to linear rgb domain
'''
def draw_centered_texture(op, settings, tx, center=[0,0], rds=1, \
                            use_mask=True, convert_srgb=False):
    centered_tex_fsh = '''
        #define PI 3.1415926538
        uniform sampler2D tex;  
        uniform float rad_tex;
        uniform bool use_mask;
        uniform bool convert_srgb;
        uniform float aa_eps;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;      

        void main()
        {        
            float aspect_ratio = textureSize(tex,0).x / float(textureSize(tex,0).y);
            float w = 2*rad_tex;
            float h = 2*rad_tex;
            if(aspect_ratio > 1){
                w *= aspect_ratio;
            }
            else{
                h /= aspect_ratio;
            }
            vec2 uv_tex = lpos/(vec2(w,h)) + vec2(0.5);

            float dst = length(lpos);
            fragColor = texture(tex,uv_tex);
            
            if(use_mask){
                fragColor.a *= aa_circle(rad_tex, dst, aa_eps);
            }

            if(convert_srgb){
                fragColor = srgb_to_linear_rgb(fragColor);
            }
        }
    '''
    abs_origin = np.asarray(op.origin) + np.asarray(center)
    shader, batch = setup_shader(op, settings, fragsh=centered_tex_fsh, origin=abs_origin, dimension=rds*2.5)
    shader.uniform_sampler("tex", tx)
    shader.uniform_float("rad_tex", rds)
    shader.uniform_bool("use_mask", [use_mask])  
    shader.uniform_bool("convert_srgb", [convert_srgb])   
    shader.uniform_float("aa_eps",settings.anti_aliasing_eps)    
    batch.draw(shader)

''' --- Drawing functions --- '''

''' Sets up a shader program to draw an image in the dimensions given in the settings '''
def setup_shader(op, settings, fragsh, libsh=common_libsh, \
                    dimension = -1, origin = None):
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
    shader = gpu.types.GPUShader(vsh, fragsh, libcode=libsh)

        # Simple screen quad
    if dimension < 0:
        dimension = settings.mat_centers_radius + 2*settings.mat_radius
    if origin is None:
        origin = op.origin
    vdata = np.asarray(((-1, 1), (-1, -1),(1, -1), (1, 1)))
    vertices = np.ndarray.tolist(vdata)        
    indices = ((0, 1, 2), (0, 2, 3))
    
    batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
    shader.bind() 
    
        # Set up uniform variables
    matrix = gpu.matrix.get_projection_matrix()*gpu.matrix.get_model_view_matrix()
    shader.uniform_float("modelViewProjectionMatrix", matrix)     
    shader.uniform_float("dimension",dimension)
    shader.uniform_float("origin", origin)

    return shader,batch 

''' In the case of "from active" material mode, or if there is no image in palette
    Draws a simple pie circle in the colors and scale given by the settings
'''
def draw_pie_circle(op, settings): 
    pie_circle_fsh = '''
        #define PI 3.1415926538
        uniform vec4 circle_color;
        uniform float inner_radius;
        uniform float outer_radius;
        uniform vec4 line_color;
        uniform float line_width;
        uniform float aa_eps;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;   

        void main()
        {                    
            float d = length(lpos);
            fragColor = vec4(0.);

            vec4 fill_color_ = circle_color;
            vec4 stroke_color = line_color;

            fill_color_.a *= aa_donut(outer_radius, inner_radius, d, aa_eps);
            stroke_color.a *= aa_contour(inner_radius, line_width, d, aa_eps);

            vec4 fragColor_main = alpha_compose(stroke_color, fill_color_);     
            fragColor = alpha_compose(fragColor_main, fragColor);
        }
    '''    

    shader, batch = setup_shader(op, settings, pie_circle_fsh)
    
    shader.uniform_float("circle_color", settings.mc_fill_color)
    shader.uniform_float("inner_radius", settings.mc_inner_radius)
    shader.uniform_float("outer_radius", settings.mc_outer_radius)
    shader.uniform_float("line_color", settings.mc_line_color)
    shader.uniform_float("line_width", settings.mc_line_width)  
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    batch.draw(shader) 


''' Draws materials picklines if there are some
'''
def draw_picklines(op, cache, settings):
    picklines_fsh = '''
    #define PI 3.1415926538
    uniform float selected_radius;
    uniform float mat_radius;
    uniform float mat_centers_radius;
    uniform int mat_selected;
    uniform float mat_thetas[__NMAT__];
    uniform vec3 mat_picklines[__NPLM__];
    uniform float pickline_width;
    uniform vec4 pickline_color;
    uniform float aa_eps;

    in vec2 lpos;
    in vec2 uv;
    out vec4 fragColor;            

    void main()
    {                    
        float d = length(lpos);
        fragColor = vec4(0.);

        /* Pick lines */
        for(int k = 0; k < __NPLM__; ++k){
            int i = int(mat_picklines[k].z);
            bool is_selected = (i == mat_selected);

            float th_i = mat_thetas[i];
            float R = is_selected?(mat_centers_radius + selected_radius - mat_radius):mat_centers_radius;
            float radius = is_selected?selected_radius:mat_radius;

            float rds = (R-radius);
            vec2 s0 = rds*mat_picklines[k].xy;
            vec2 s1 = rds*vec2(cos(th_i), sin(th_i));

            vec4 fragColor_line = pickline_color;
            fragColor_line.a *= ((mat_selected >=0) && !is_selected)?0.3:1;
            fragColor_line.a *= aa_seg(s0, s1, lpos, pickline_width, aa_eps);

            fragColor = alpha_compose(fragColor, fragColor_line);
        }

    }
    '''
    picklines = cache.get_picklines()
    nplm = len(picklines)
    if nplm == 0:     
        return

    fsh = picklines_fsh
    fsh = fsh.replace("__NPLM__",str(nplm))
    fsh = fsh.replace("__NMAT__",str(cache.mat_nb))

    shader, batch = setup_shader(op, settings, fsh)

    shader.uniform_float("selected_radius", settings.selected_radius)
    shader.uniform_float("mat_radius", settings.mat_radius)
    shader.uniform_float("mat_centers_radius", settings.mat_centers_radius)
    shader.uniform_int("mat_selected", op.mat_selected);   
    set_uniform_vector_float(shader, cache.angles, "mat_thetas") 
    set_uniform_vector_float(shader, picklines, "mat_picklines")
    shader.uniform_float("pickline_width", settings.pickline_width)
    shader.uniform_float("pickline_color", settings.mc_line_color)
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps)
    
    batch.draw(shader)


''' Draws a dot mark to spot the active material '''
def draw_active(op, cache, settings):
    color = settings.active_color
    radius = settings.mat_line_width
    th = cache.angles[cache.mat_active]
    from math import cos, sin
    mat_radius = settings.mat_radius
    if op.mat_selected == cache.mat_active:
        mat_radius = settings.selected_radius
    R = settings.mat_centers_radius + mat_radius + settings.mat_line_width*2.5
    pos = R*np.asarray([cos(th), sin(th)])
    draw_mark(op, settings, pos, radius, color)

''' Draws the preview image of brushes '''
def draw_bsh_previews(op, context, cache, settings, mat_id):
    bnames = cache.map_bsh[mat_id]
    brushes = [b for b in cache.brushes if b.name in bnames]
    th = cache.angles[mat_id]
    from math import cos, sin
    mat_dir = np.asarray([cos(th), sin(th)])
    R = settings.mat_centers_radius
    radius = settings.mat_radius
    r = settings.selected_radius + radius*1.5
    for b in brushes:
        tex = cache.bsh_prv[b.name]
        if not tex:
            continue
        center = (R+r)*mat_dir
        draw_centered_texture(op, settings, tex, center, radius)
        r += radius*2.5

''' Draws the preview image of materials '''
def draw_mat_previews(op, context, cache, settings):
    mat_prv_fsh = '''
        #define PI 3.1415926538
        uniform sampler2D tex;  
        uniform float radius;
        uniform float aa_eps;
        uniform float th_i;
        uniform float R;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;   

        void main()
        {          
            /* compute the center of circle */
            vec2 ci = R*vec2(cos(th_i),sin(th_i));
            float d = length(lpos-ci);    

            if( d > radius + aa_eps*2 ){
                fragColor = vec4(0.);
                return;
            }

            float aspect_ratio = textureSize(tex,0).x / float(textureSize(tex,0).y);
            float w = 2*radius;
            float h = 2*radius;
            if(aspect_ratio > 1){
                w *= aspect_ratio;
            }
            else{
                h *= aspect_ratio;
            }
            vec2 uv_tex = (lpos-ci)/(vec2(w,h)) + vec2(0.5);

            fragColor = srgb_to_linear_rgb(texture(tex, uv_tex));
        }
    '''
    flat_prv_fsh = '''
        #define PI 3.1415926538
        uniform vec4 fill_color;
        uniform vec4 line_color;
        uniform float mat_line_width;
        uniform float radius;
        uniform float aa_eps;
        uniform float th_i;
        uniform float R;

        in vec2 lpos;
        in vec2 uv;
        out vec4 fragColor;   

        void main()
        {          
            /* compute the center of circle */
            vec2 ci = R*vec2(cos(th_i),sin(th_i));
            float d = length(lpos-ci);    

            if( d > radius + aa_eps*2 ){
                fragColor = vec4(0.);
                return;
            } 

            /* draw circle */
            vec4 fcolor = fill_color;
            vec4 lcolor = line_color;
            fcolor.a *= aa_circle(radius, d, aa_eps);
            lcolor.a *= aa_contour(radius, mat_line_width, d, aa_eps);

            fragColor = alpha_compose(lcolor, fcolor);
        }
    '''
    for mat_id in range(cache.mat_nb):
        # tx = cache.mat_prv[mat_id]
        tx = None
        if tx:
            fsh = mat_prv_fsh
        else:
            fsh = flat_prv_fsh

        th = cache.angles[mat_id]
        if op.mat_selected == mat_id:
            rds = settings.selected_radius
            R = settings.mat_centers_radius + rds - settings.mat_radius
        else:
            rds = settings.mat_radius
            R = settings.mat_centers_radius
        
        shader, batch = setup_shader(op, settings, fsh)
        if tx:
            shader.uniform_sampler("tex",tx)
            rds *= 1.3
        else:
            shader.uniform_float("fill_color", cache.mat_fill_colors[mat_id])
            shader.uniform_float("line_color", cache.mat_line_colors[mat_id])
            shader.uniform_float("mat_line_width", settings.mat_line_width)
        shader.uniform_float("radius",rds)    
        shader.uniform_float("th_i", th)    
        shader.uniform_float("R", R)    
        shader.uniform_float("aa_eps",settings.anti_aliasing_eps)    
        batch.draw(shader) 


''' Draws the image of the palette in the middle of the icon '''
def draw_palette_image(op, context, cache, settings):
    gpmp = context.scene.gpmatpalettes.active()
    sid = op.mat_selected

    if (gpmp.name == cache.pal_active) and \
         (sid == cache.mat_cached) :
        tx = cache.gpu_texture
    elif ( sid == -1 ) or ( not gpmp.materials[sid].image ):
        tx = load_gpu_texture(gpmp.image)
    else:
        tx = load_gpu_texture(gpmp.materials[sid].image) 
    
    if not tx:
        return

    rds = settings.tex_radius  
    draw_centered_texture(op, settings, tx, rds=rds, use_mask=True)

    cache.gpu_tex = tx
    cache.mat_cached = sid
    cache.pal_active = gpmp.name

''' --- Writing functions --- '''

''' Useful function to write text centered in a circle of origin org, and of radius ird'''
def write_circle_centered(settings, org, ird, text):
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

''' Writes the name of the selected material '''
def write_selected_mat_name(op, cache, settings):
    txt = cache.materials[op.mat_selected].name
    org = op.origin + 0.5*op.region_dim
    org[1] = org[1] - (settings.mat_centers_radius+2*settings.mat_radius)
    org[1] = org[1] - settings.text_size
    ird = settings.mc_outer_radius
    write_circle_centered(settings, org, ird, txt)

''' Writes the name of the active palette '''
def write_active_palette(op, context, settings):
    plt = context.scene.gpmatpalettes.active()
    if not plt:
        return
    txt = plt.name
    org = op.origin + 0.5*op.region_dim
    org[1] = org[1] - (settings.mat_centers_radius+2*settings.mat_radius)
    ird = settings.mc_outer_radius
    write_circle_centered(settings, org, ird, txt)


''' Main Drawing function for the GP Color Picker'''
def draw_callback_px(op, context, cache, settings): 
    gpu.state.blend_set('ALPHA')   

    if op.mat_selected >= 0:
        write_selected_mat_name(op, cache, settings)
        
    if cache.use_gpu_texture():
        draw_palette_image(op, context, cache, settings)
    else:
        draw_pie_circle(op, settings)

    if cache.mat_active >= 0:
        draw_active(op, cache, settings) 

    draw_picklines(op, cache, settings)
    draw_mat_previews(op, context, cache, settings)

    if op.mat_selected >= 0:
        draw_bsh_previews(op, context, cache, settings, mat_id=op.mat_selected)
        
    if cache.from_palette:
        write_active_palette(op, context, settings)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    op.check_time()
    