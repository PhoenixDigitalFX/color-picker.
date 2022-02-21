import numpy as np
from math import floor, ceil, pi, sin, asin

class GPCOLORPICKER_settings():
    def __init__(self, prefs = None):
        # Const values
        self.switch_key = 'TAB'
        self.active_color =  (0.05,0.05,0.05,1)
        self.mat_line_width = 5.
        self.mc_line_width = 1.
        self.anti_aliasing_eps = 0.5

        # From user preferences
        if prefs:
            self.mat_from_active = (prefs.mat_mode == "from_active")
            self.mat_assign = prefs.assign_mat
            self.mc_fill_color = prefs.theme.pie_color
            self.mc_line_color = prefs.theme.line_color
            self.text_color = prefs.theme.text_color
            self.set_icon_scale(prefs.icon_scale)
        else:
            self.mat_from_active = True
            self.mat_assign = False
            self.mc_fill_color = (0.4,0.4,0.4,1.)
            self.mc_line_color = (0.96,0.96,0.96,1.)
            self.text_color = (0.,0.,0.,1.)
            self.set_icon_scale(250)

        # # OLD
        # self.origin = np.asarray([0,0])
        # self.region_dim = np.asarray([0,0])

        # # context 
        # self.active_obj = None
        # self.materials = []
        # self.mat_nb = -1
        # self.mat_selected =  -1
        # self.mat_active =  -1
        # self.mat_fill_colors = []
        # self.mat_line_colors = []
        # self.custom_angles = []

        # # cached
        # self.cached_gpu_tex = None
        # self.cached_mat_selected = -1
        # self.cached_palette_name = ""

    def set_icon_scale(self,scale):
        self.icon_scale = scale
        self.mat_centers_radius = self.icon_scale/(2*(1.2))
        self.mc_outer_radius = 0.9*self.mat_centers_radius
        self.mc_inner_radius = 0.6*self.mc_outer_radius
        self.interaction_radius = 0.5*self.mc_outer_radius

        self.mat_rmin = 5
        self.mat_rmax = 0.1*self.mat_centers_radius
        self.mat_radius = self.mat_rmax

        self.selected_radius = 1.2*self.mat_radius
        self.mat_nmax = floor(pi/asin(self.mat_rmin/self.mat_centers_radius))
        self.text_size = ceil(0.08*self.icon_scale)
        self.tex_radius = self.mat_centers_radius-self.mat_radius

    def load_mat_radius(self):
        if self.mat_nb <= 1:
            return self.mat_rmax
        r_opt = 0.8*self.mat_centers_radius*sin(pi/self.mat_nb)
        self.mat_radius = max(self.mat_rmin,min(r_opt,self.mat_rmax))
        self.selected_radius = self.mat_radius*1.2
        self.tex_radius = self.mat_centers_radius-self.mat_radius
        return self.mat_radius

    # def useGPUTexture(self):
    #     return (not self.mat_from_active) and self.cached_gpu_tex
    
    # def useCustomAngles(self):
    #     return (not self.mat_from_active) and self.custom_angles