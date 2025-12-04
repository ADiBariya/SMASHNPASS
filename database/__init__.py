# database/__init__.py

from database.mongo import Database

db = Database()

__all__ = ["db"]