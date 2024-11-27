# Custom Exception    
class UnsupportedGeometryException(Exception):
    """ Custom Exception to indicate that the geometry is not supported """
    def __init__(self, message='Cannot Parse - Unsupported Geometry Type'):
        super().__init__(message)