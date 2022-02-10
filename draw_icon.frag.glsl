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
    float alpha = 0.5*(mat_thetas[0] + mat_thetas[mat_nb-1]);
    int i = 0;
    // specific case of i = 0
    if ( (dt >= 0.5*(mat_thetas[0] + mat_thetas[1])) 
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