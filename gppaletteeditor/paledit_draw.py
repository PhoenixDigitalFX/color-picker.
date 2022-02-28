import blf, bpy
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *
import os
from .. gpcolorpicker import picker_draw as gpcp

edition_layer_fsh = '''
#define PI 3.1415926538
uniform vec2 mat_origin;
uniform vec4 picker_color;
uniform float mark_radius;
uniform float aa_eps;

in vec2 lpos;
in vec2 uv;
out vec4 fragColor;   

float aa_circle(float rds, float dst, float eps){
    return smoothstep(rds+eps, rds-eps, dst);
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
    float d = length(lpos-mat_origin);  

    vec4 fragColor_origin= picker_color;
    fragColor_origin.a *= aa_circle(mark_radius, d, aa_eps); 
    fragColor = fragColor_origin;  
}
'''

def draw_edition_layer(op, context, cache, settings):
    nmat = cache.mat_nb
    if nmat <= 0:
        return    

    fsh = edition_layer_fsh
    fsh = fsh.replace("__NMAT__",str(nmat))

    shader, batch = gpcp.setup_shader(op, settings, fsh)

    R = settings.mat_centers_radius - settings.mat_radius
    origin = R*cache.pick_origins[op.origin_selected][0:2]

    shader.uniform_float("mat_origin", origin) 
    shader.uniform_float("mark_radius", settings.mat_line_width) 
    shader.uniform_float("picker_color", settings.mc_line_color) 
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps) 

    batch.draw(shader)  


def draw_callback_px(op, context, cache, settings): 
    gpcp.draw_callback_px(op, context, cache, settings)  

    gpu.state.blend_set('ALPHA') 
    
    if op.origin_selected >= 0:
        draw_edition_layer(op, context, cache, settings)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    # op.check_time()
    