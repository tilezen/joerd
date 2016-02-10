from osgeo import osr

WGS84_WKT = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,' \
            '298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0]' \
            ',AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY[' \
            '"EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY[' \
            '"EPSG","9108"]],AUTHORITY["EPSG","4326"]]'


def wgs84():
    sr = osr.SpatialReference()
    sr.ImportFromWkt(WGS84_WKT)
    return sr
