# Miscellanous useful functions

def srgb_to_linearrgb(c):
    '''from https://blender.stackexchange.com/a/158902/4979'''
    if   c < 0:       return 0
    elif c < 0.04045: return c/12.92
    else:             return ((c+0.055)/1.055)**2.4

def hex2rgba(hex, alpha):
    '''from https://blender.stackexchange.com/a/158902/4979'''
    h = hex
    if type(h) is str:
        h = int(h, 16)
    r = (h & 0xff0000) >> 16
    g = (h & 0x00ff00) >> 8
    b = (h & 0x0000ff)
    return tuple([srgb_to_linearrgb(c/0xff) for c in (r,g,b)] + [alpha])

''' Get all intervals of value -1 in a list containing sorted values and -1 '''
def get_unset_intervals(sorted_items):
    nit = len(sorted_items)

    def is_set(i):
        return sorted_items[i][0] >= 0

    if not any([is_set(i) for i in range(nit)]):
        return [ (0, 0, [k for _,k in sorted_items]) ]
    
    def next_item(i, increasing_order=True):
        if increasing_order:
            return (i + 1)% nit
        return (i - 1)% nit

    def get_first_set_item():
        i = 0
        while not is_set(i):
            i = next_item(i, False)
        return i
    
    def get_following_set_item(s):
        n = next_item(s)
        while not is_set(n):
            n = next_item(n)
        return n

    def get_ids_between(s, e):
        ids = []
        n = next_item(s)
        while( n != e ):
            ids.append(sorted_items[n][1])
            n = next_item(n)
        return ids
    
    intervals = []
    i = get_first_set_item()
    s = i
    e = get_following_set_item(s)
    while(e != i):
        e = get_following_set_item(s)
        ids = get_ids_between(s,e)
        if not ids:
            s = e
            continue

        alpha = sorted_items[s][0]
        beta = sorted_items[e][0]
        intervals.append( (alpha, beta, ids) )

        s = e
    
    return intervals