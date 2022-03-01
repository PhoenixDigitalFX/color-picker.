import blf, bpy
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *
import os
from .. gpcolorpicker import picker_draw as gpcp

edition_layer_fsh = '''
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

void main()
{                    
    if(mark_type == 0){
        fragColor = draw_circle_mark();
    }
    else if(mark_type == 1){
        fragColor = draw_cross_mark();
    }
    else{
        fragColor = vec4(0.);
    }
}
'''

def draw_edition_layer(op, context, cache, settings):
    shader, batch = gpcp.setup_shader(op, settings, edition_layer_fsh)

    mark = op.interaction_in_selection.mark
    shader.uniform_float("mark_origin", mark.position) 
    shader.uniform_float("mark_radius", mark.radius) 
    shader.uniform_float("mark_color", mark.color) 
    shader.uniform_int("mark_type", mark.type) 
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps) 

    batch.draw(shader)  

empty_palette_fsh = '''
#define PI 3.1415926538
uniform vec2 empty_origin;
uniform vec4 empty_color;
uniform float empty_radius;
uniform float aa_eps;

in vec2 lpos;
in vec2 uv;
out vec4 fragColor;      

void main()
{     
    float d = length(lpos-empty_origin); 
    fragColor = empty_color;
    fragColor.a *= aa_circle(empty_radius, d, aa_eps); 
  
}
'''
def draw_empty_palette(op, context, settings):
    shader, batch = gpcp.setup_shader(op, settings, empty_palette_fsh)

    shader.uniform_float("empty_origin", np.zeros(2)) 
    shader.uniform_float("empty_radius", settings.mc_outer_radius) 
    shader.uniform_float("empty_color", settings.mc_fill_color) 
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps) 

    batch.draw(shader)  

def draw_callback_px(op, context, cache, settings): 

    if op.empty_palette:
        gpu.state.blend_set('ALPHA') 
        draw_empty_palette(op, context, settings)
    else:
        gpcp.draw_callback_px(op, context, cache, settings)  
        gpu.state.blend_set('ALPHA') 
    
    if op.interaction_in_selection and op.interaction_in_selection.has_mark():
        draw_edition_layer(op, context, cache, settings)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    # op.check_time()
    