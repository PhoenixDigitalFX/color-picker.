import blf, bpy
import gpu
from gpu_extras.batch import batch_for_shader
import numpy as np
from math import *
import os
from .. gpcolorpicker import picker_draw as gpcp

edition_layer_fsh = '''
#define PI 3.1415926538

float aa_circle(float rds, float dst, float eps){
    return smoothstep(rds+eps, rds-eps, dst);
}        

void main()
{                    
    float d = length(lpos);
    in vec2 lpos;
    in vec2 uv;
    out vec4 fragColor;         

    /*    MATERIALS CIRCLES    */
    /* find optimal circle index for current location */
    vec2 loc_pos = lpos;
    float dt = mod(atan(loc_pos.y, loc_pos.x),2*PI);
    int i = 0;

    if( dt < 0 ){
        dt += 2*PI;
    }
    if( mat_nb > 1 ){
        // specific case of i = 0       
        float alpha = 0.5*(mat_thetas[0] + mat_thetas[mat_nb-1] - 2*PI);
        alpha = (alpha < 0)?(alpha + 2*PI):alpha;
        float beta = 0.5*(mat_thetas[0] + mat_thetas[1 % mat_nb]);

        bool in_first_interval = ((alpha < beta) && in_interval(dt, alpha, beta) );
        in_first_interval = in_first_interval || ((alpha >= beta) && ( (dt <= beta) || (dt >= alpha) ));

        if ( !in_first_interval ){
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

    
    /* compute the center of circle */
    float th_i = mat_thetas[i];
    vec2 ci = R*vec2(cos(th_i),sin(th_i));
    d = length(lpos-ci);     
            
    /* draw circle */
    fragColor = alpha_compose(fragColor_mat, fragColor_main);        

}
'''
def draw_callback_px(op, context, cache, settings): 
    gpu.state.blend_set('ALPHA')   

    if op.mat_selected >= 0:
        gpcp.write_selected_mat_name(op, cache, settings)
        
    if cache.use_gpu_texture():
        gpcp.draw_centered_texture(op, context, cache, settings)

    gpcp.draw_main_circle(op, cache, settings)  

    if cache.from_palette:
        gpcp.write_active_palette(op, context, settings)

    # Reset blend mode
    gpu.state.blend_set('NONE')
    # op.check_time()
    