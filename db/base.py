from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """
    Clase Base única para todo el proyecto. 
    Esto garantiza que el registro de SQLAlchemy sea global y único.
    """
    pass
