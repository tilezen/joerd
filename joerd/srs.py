from osgeo import osr

WGS84_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,' \
            '298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0]' \
            ',AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY[' \
            '"EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY[' \
            '"EPSG","9108"]],AUTHORITY["EPSG","4326"]]'


NAD83_WKT = 'GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID[' \
            '"GRS 1980",6378137,298.2572221010002,AUTHORITY["EPSG","7019"]],' \
            'AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0],UNIT["degree",' \
            '0.0174532925199433],AUTHORITY["EPSG","4269"]]'

D96_WKT = 'PROJCS["Slovenia 1996 / Slovene National Grid",GEOGCS["Slovenia 1996",' \
'DATUM["Slovenia_Geodetic_Datum_1996",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],' \
'TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6765"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],' \
'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4765"]],PROJECTION["Transverse_Mercator"],' \
'PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",15],PARAMETER["scale_factor",0.9999],' \
'PARAMETER["false_easting",500000],PARAMETER["false_northing",-5000000],UNIT["metre",1,AUTHORITY["EPSG","9001"]],' \
'AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","3794"]]'



def wgs84():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(WGS84_WKT)
    return sr


def nad83():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(NAD83_WKT)
    return sr

def d96():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(D96_WKT)
    return sr