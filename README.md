# Oracle Geometry Parser

A small package intended to convert [shapely](https://shapely.readthedocs.io/en/2.0.4/index.html) geometry objects to Oracle Spatial compatible geometry types for use in database insert pipelines following a [geopandas](https://geopandas.org/en/latest/index.html) or [shapely](https://shapely.readthedocs.io/en/2.0.4/index.html) analysis process. 

Coordinate Reference Systems are supported and if passed as an argument, the resultant SDO geometry with be assigned the provided crs. This is only designed to work with 2D geometries. Shapely ignores the Z coordinate by default. If 3D data is parsed, the input into Oracle will be in 2D.

# Requirements
- [Oracle Client](https://www.oracle.com/au/database/technologies/oracle19c-windows-downloads.html) - tested on Version 19c
- [oracledb](https://python-oracledb.readthedocs.io/en/v2.1.1/) - tested on version 2.1.1
- [shapely](https://shapely.readthedocs.io/en/2.0.4/index.html) - tested on version 2.0.4
- [numpy](https://numpy.org/doc/1.26/) - tested on version 1.26.4

# Set Up
To set up, simply run pip install in a python command prompt:
```
pip install dbgeomparser
```

# Example
The below code block depicts the a simple use case of the module - inserting a single shapely point geometry into an oracle table. Extentions of this methodology include parsing all geometries in a GeoDataFrame and inserting the entire dataset into an oracle table.

```
import oracledb
import shapely as shp
from dbgeomparser import OracleGeomParser

### Oracle Connection ###
connection = oracledb.connect(user = 'Your Username', 
                              password = 'Your Password', 
                              host = 'localhost', 
                              port = 1521, 
                              dsn = 'Your dsn')
cursor = connection.cursor()

### Geometry Parser ###
parser = OracleGeomParser(connection) 

test_geometry = shp.Point(1, 1)
sdo_geom = parser.parse_geometry(test_geometry) 

# Can specify a crs if required by passing the parameter 'crs' as an argument 
# e.g. parser.parse_geometry(test_geometry, crs = 4326) where the value is an EPSG code.
# print(sdo_geom) will print something like this: 
# <oracledb.DbObject MDSYS.SDO_GEOMETRY at 0x2ae4d370170>
# indicating the conversion has been successful.

### Example Insert Statement ###
sql = "INSERT INTO SCHEMA_NAME.TABLE_NAME (GEOMETRY_COLUMN) VALUES (:1)"
cursor.execute(sql, [parser.parse_geometry(geom)])
connection.commit()
```