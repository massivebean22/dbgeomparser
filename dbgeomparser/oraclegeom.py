import oracledb
import shapely as shp
import numpy as np
from .custom_exceptions import UnsupportedGeometryException

class OracleGeomParser:
    """ Object that handles conversion of shapely Geometry to relevant ORACLE SDO_GEOMETRY OBJECT """

    def __init__(self, connection: oracledb.Connection):
        """
        Constructor that connects to an Oracle Database and retrieves the relevant
        Oracle data types for geometry parsing. 

        Arguments:
        |-> connection: an oracle database connection
        """
        ### Retrieves relevant SDO data types to assist with Oracle Geometry Creation
        self.geom_type_obj = connection.gettype("MDSYS.SDO_GEOMETRY")
        self.element_info_type_obj = connection.gettype("MDSYS.SDO_ELEM_INFO_ARRAY")
        self.ordinate_type_obj = connection.gettype("MDSYS.SDO_ORDINATE_ARRAY")
        self.point_type_obj = connection.gettype("MDSYS.SDO_POINT_TYPE")

    ### Main Parsing Function
    def parse_geometry(self, geom:shp.Geometry, crs:int = None, base_data:bool = False):
        """
        Converts a shapely geometry object into an ORACLE SDO_GEOMETRY object.
        Primarily for use with insertion into a database following a python / 
        geopandas / shapely analysis process. 

        WARNING - 3D Data is not accounted for in this process. If 3D data is parsed,
        The input into ORACLE will be in 2D.

        Arguments:
        |-> geom: a shapely geometry object
        |-> crs: the EPSG code / coordinate reference system of the input geometry (optional)
        |-> base_data: optional boolean to return the SDO_ELEM_INFO array and the Ordinates
                       rather than returning a MDSYS.SDO_GEOMETRY Object - DOES NOT RETURN
                       SDO_ELEM_INFO or Ordinates when using this specific function but will
                       return it if the sub functions are called

        Returns:
        |-> None if shapely geometry type is not supported or if the data is 3D 
        |-> MDSYS.SDO_GEOMETRY object
        """

        geom_type = geom.geom_type
        
        match geom_type:
            case 'Point':
                return self.create_point(geom, crs, base_data)
            case 'LineString':
                return self.create_line(geom, crs, base_data)
            case 'LinearRing':
                return self.create_line(geom, crs, base_data)
            case 'Polygon':
                return self.create_polygon(geom, crs, base_data)
            case 'GeometryCollection':
                return self.create_geometry_collection(geom, crs, base_data)
            case 'MultiPoint':
                return self.create_multipoint(geom, crs, base_data)
            case 'MultiLineString':
                return self.create_multiline(geom, crs, base_data)
            case 'MultiPolygon':
                return self.create_multipolygon(geom, crs, base_data)
            case _:
                print(f'Geometry Type < {geom_type} > is not currently supported! Parse Failed!')
                raise UnsupportedGeometryException

    def create_point(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a shapely Point into an ORACLE Point
        """
        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        geometry.SDO_GTYPE = 2001
        geometry.SDO_POINT = self.point_type_obj.newobject()
        geometry.SDO_POINT.X = geom.x
        geometry.SDO_POINT.Y = geom.y

        if base_data:
            elem_info = [1, 1, 1]
            ordinates = [geom.x, geom.y]
            return {'elem_info':elem_info, 'ordinates':ordinates}
        
        return geometry

    def create_line(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """ 
        Converts a shapely LineString or LinearRing to an ORACLE Line 
        """
        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        ordinates = []
        for point in shp.get_coordinates(geom):
            for coord in point:
                ordinates.append(coord)

        elem_info = [1, 2, 1]

        geometry.SDO_GTYPE = 2002
        geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
        geometry.SDO_ELEM_INFO.extend(elem_info)
        geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
        geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}

        return geometry

    def create_polygon(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a Shapely Polygon into an ORACLE Polygon
        Can handle simple and complex polygons (polygons with holes)
        """
        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        ordinates = []

        # Simple Polygon with No Holes  
        if shp.get_num_interior_rings(geom) == 0:
            
            for point in shp.get_coordinates(geom):
                for coord in point:
                    ordinates.append(coord) 

            elem_info = [1, 1003, 1]

            geometry.SDO_GTYPE = 2003
            geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
            geometry.SDO_ELEM_INFO.extend(elem_info)
            geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
            geometry.SDO_ORDINATES.extend(ordinates)
        
        # Polygon with Holes
        else: 
            rings = shp.get_rings(geom)
            elem_info = []
            coord_count = 0

            for index, ring in enumerate(rings):

                if index == 0: 
                    # Outer Ring -> coordinates must be anti-clockwise
                    elem_info.extend([1, 1003, 1])
                    for point in np.flip(shp.get_coordinates(ring),0):
                        for coord in point:
                            ordinates.append(coord)
                            coord_count += 1
                else: 
                    # Inner Rings
                    elem_info.extend([coord_count + 1, 2003, 1])
                    for point in shp.get_coordinates(ring):
                        for coord in point:
                            ordinates.append(coord)
                            coord_count += 1
            
            geometry.SDO_GTYPE = 2003
            geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
            geometry.SDO_ELEM_INFO.extend(elem_info)
            geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
            geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}
        
        return geometry

    def create_geometry_collection(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a shapely GeometryCollection to an ORACLE Collection
        """
        geom_list = geom.geoms
        sdo_geom_data = []

        for index, item in enumerate(geom_list):
            sdo_geom_data.append(self.parse_geometry(item, crs, True))

        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        elem_info = []
        ordinates = []
        coord_count = 0

        for index, item in enumerate(sdo_geom_data):
            if index > 0:
                # Offset the start index new elements by the coord count 
                for i in range(0, len(item['elem_info'])):
                    if i % 3 == 0:
                        item['elem_info'][i] += coord_count

            elem_info.extend(item['elem_info'])
            ordinates.extend(item['ordinates'])
            coord_count += len(item['ordinates'])

        geometry.SDO_GTYPE = 2004
        geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
        geometry.SDO_ELEM_INFO.extend(elem_info)
        geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
        geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}

        return geometry

    def create_multipoint(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a Shapely MultiPoint to a ORACLE MultiPoint
        """
        geom_list = geom.geoms
        sdo_geom_data = []

        for index, item in enumerate(geom_list):
            sdo_geom_data.append(self.parse_geometry(item, crs, True))

        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        elem_info = []
        ordinates = []
        coord_count = 0

        for index, item in enumerate(sdo_geom_data):
            if index > 0:
                # Offset the start index new elements by the coord count 
                for i in range(0, len(item['elem_info'])):
                    if i % 3 == 0:
                        item['elem_info'][i] += coord_count

            elem_info.extend(item['elem_info'])
            ordinates.extend(item['ordinates'])
            coord_count += len(item['ordinates'])

        geometry.SDO_GTYPE = 2005
        geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
        geometry.SDO_ELEM_INFO.extend(elem_info)
        geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
        geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}
        
        return geometry

    def create_multiline(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a Shapely MultiLineString to a ORACLE MultiLine
        """
        geom_list = geom.geoms
        sdo_geom_data = []

        for index, item in enumerate(geom_list):
            sdo_geom_data.append(self.parse_geometry(item, crs, True))

        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        elem_info = []
        ordinates = []
        coord_count = 0

        for index, item in enumerate(sdo_geom_data):
            if index > 0:
                # Offset the start index new elements by the coord count 
                for i in range(0, len(item['elem_info'])):
                    if i % 3 == 0:
                        item['elem_info'][i] += coord_count

            elem_info.extend(item['elem_info'])
            ordinates.extend(item['ordinates'])
            coord_count += len(item['ordinates'])

        geometry.SDO_GTYPE = 2006
        geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
        geometry.SDO_ELEM_INFO.extend(elem_info)
        geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
        geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}
        
        return geometry

    def create_multipolygon(self, geom:shp.Geometry, crs:str, base_data:bool = False):
        """
        Converts a Shapely MultiPolygon to a ORACLE MultiPolygon
        """
        geom_list = geom.geoms
        sdo_geom_data = []

        for index, item in enumerate(geom_list):
            sdo_geom_data.append(self.parse_geometry(item, crs, True))

        geometry = self.geom_type_obj.newobject()

        if crs != None:
            geometry.SDO_SRID = crs

        elem_info = []
        ordinates = []
        coord_count = 0

        for index, item in enumerate(sdo_geom_data):
            if index > 0:
                # Offset the start index new elements by the coord count 
                for i in range(0, len(item['elem_info'])):
                    if i % 3 == 0:
                        item['elem_info'][i] += coord_count

            elem_info.extend(item['elem_info'])
            ordinates.extend(item['ordinates'])
            coord_count += len(item['ordinates'])

        geometry.SDO_GTYPE = 2007
        geometry.SDO_ELEM_INFO = self.element_info_type_obj.newobject()
        geometry.SDO_ELEM_INFO.extend(elem_info)
        geometry.SDO_ORDINATES = self.ordinate_type_obj.newobject()
        geometry.SDO_ORDINATES.extend(ordinates)

        if base_data:
            return {'elem_info':elem_info, 'ordinates':ordinates}
        
        return geometry

