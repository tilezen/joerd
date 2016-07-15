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


def wgs84():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(WGS84_WKT)
    return sr


def nad83():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(NAD83_WKT)
    return sr
