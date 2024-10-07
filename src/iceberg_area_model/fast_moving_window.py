import numpy as np
import numba as nb

"""
Fast functions for CFAR moving window. Code modified froms: Laust Færch (https://github.com/LaustFaerch/cfar-object-detection)
"""

@nb.jit('float32[:,:](float32[:,:], boolean[:,:])', parallel=True, nopython=True)
def fast_edge_nanmean29(x, m):
    return _edge_kernel_nanmean29(x, m)

@nb.jit('float32[:,:](float32[:,:], boolean[:,:])', parallel=True, nopython=True)
def fast_edge_nanmean49(x, m):
    return _edge_kernel_nanmean49(x, m)

# outer_window_size==29
@nb.stencil(neighborhood=((-14, 14), (-14, 14)))
def _edge_kernel_nanmean29(x, m):
    if m[0, 0]:
        cumul = 0
        valids = 0
        for i in range(-14, 15):
            for ii in range(-14, 15):
                # inner_window_size==21
                if (i < -10 or i > 10) or (ii < -10 or ii > 10):
                    if ~np.isnan(x[i, ii]):
                        cumul += x[i, ii]
                        valids += 1
        if valids == 0:
            return nb.float32(0)
        else:
            return nb.float32(cumul / valids)
    else:
        return nb.float32(np.nan)

# outer_window_size==49
@nb.stencil(neighborhood=((-24, 24), (-24, 24)))
def _edge_kernel_nanmean49(x, m):
    if m[0, 0]:
        cumul = 0
        valids = 0
        for i in range(-24, 25):
            for ii in range(-24, 25):
                # Corresponding to inner_window_size==35
                if (i < -17 or i > 17) or (ii < -17 or ii > 17):
                    if ~np.isnan(x[i, ii]):
                        cumul += x[i, ii]
                        valids += 1
        if valids == 0:
            return nb.float32(0)
        else:
            return nb.float32(cumul / valids)
    else:
        return nb.float32(np.nan)
