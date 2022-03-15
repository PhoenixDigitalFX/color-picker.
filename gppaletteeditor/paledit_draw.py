# GPU drawing related functions
# Note : drawing the palette editor icon is mainly based on the picker's drawing functions
# Only palette editor specific displays are specified here
import gpu
import numpy as np
from math import *
from .. gpcolorpicker import picker_draw as gpcp

''' Draws layer containing edition marks (defined in InteractionArea structures) '''
def draw_edition_layer(op, context, cache, settings):
    m = op.interaction_in_selection.mark
    gpcp.draw_mark(op, settings, m.position, m.radius, m.color, m.type)

''' Draws icon for adding a new palette '''
def draw_empty_palette(op, context, settings):
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
    shader, batch = gpcp.setup_shader(op, settings, empty_palette_fsh)

    shader.uniform_float("empty_origin", np.zeros(2)) 
    shader.uniform_float("empty_radius", settings.mc_outer_radius) 
    shader.uniform_float("empty_color", settings.mc_fill_color) 
    shader.uniform_float("aa_eps", settings.anti_aliasing_eps) 

    batch.draw(shader)  

''' Main Drawing function for the Palette Editor'''
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
    