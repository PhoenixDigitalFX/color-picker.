import numpy as np
from math import floor, ceil, pi, sin, asin

class GPCOLORPICKER_settings():
    def __init__(self): 
        self.key_shortcut = 'S'
        self.origin = np.asarray([0,0])
        self.active_obj = None
        self.materials = []
        self.region_dim = np.asarray([0,0])
        self.anti_aliasing_eps = 0.5

        self.mat_from_active = True
        self.mat_nb = -1
        self.mat_selected =  -1
        self.mat_active =  -1
        self.mat_fill_colors = []
        self.mat_line_colors = []
        self.gpu_tex = None
        self.custom_angles = []

        self.mc_fill_color = (0.4,0.4,0.4,1.)
        self.mc_line_color = (0.96,0.96,0.96,1.)
        self.active_color =  (0.05,0.05,0.05,1)
        self.text_color = (0.,0.,0.,1.)

        self.mat_line_width = 5.
        self.mc_line_width = 1.
        self.set_icon_scale(250)

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        self.mat_centers_radius = self.icon_scale/(2*(1.2))
        self.mc_outer_radius = 0.9*self.mat_centers_radius
        if self.useGPUTexture():
            self.mc_inner_radius = 0.0
        else:
            self.mc_inner_radius = 0.6*self.mc_outer_radius
        self.interaction_radius = 0.5*self.mc_outer_radius
        self.tex_radius = 0.8*self.mat_centers_radius

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

    def useGPUTexture(self):
        return (not self.mat_from_active) and self.gpu_tex
    
    def useCustomAngles(self):
        return (not self.mat_from_active) and self.custom_angles