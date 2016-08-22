#!/usr/bin/env python
from math import log, tan, pi

def mercator(lat, lon, zoom):
    ''' Convert latitude, longitude to z/x/y tile coordinate at given zoom.
        
        >>> mercator(0, 0, 0)
        (0, 0, 0)
        
        >>> mercator(0, 0, 16)
        (16, 32768, 32768)
        
        >>> mercator(37.79125, -122.39197, 16)
        (16, 10487, 25327)

        >>> mercator(40.74418, -73.99047, 16)
        (16, 19298, 24632)

        >>> mercator(-35.30816, 149.12446, 16)
        (16, 59915, 39645)
    '''
    # convert to radians
    x1, y1 = lon * pi/180, lat * pi/180
    
    # project to mercator
    x2, y2 = x1, log(tan(0.25 * pi + 0.5 * y1))
    
    # transform to tile space
    tiles, diameter = 2 ** zoom, 2 * pi
    x3, y3 = int(tiles * (x2 + pi) / diameter), int(tiles * (pi - y2) / diameter)
    
    return zoom, x3, y3

if __name__ == '__main__':
    import doctest
    doctest.testmod()
