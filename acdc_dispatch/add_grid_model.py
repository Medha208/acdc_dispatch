import os
from GridCal.Engine.IO.file_handler import FileOpen

def add_grid_model(file_path: str):
    """
    Load a grid model from a given file path using GridCal.

    Parameters
    ----------
    file_path : str
        Full path to the PSSE raw file (or other supported formats).

    Returns
    -------
    grid : Grid
        GridCal grid object created from the file.
    """
    abs_path = os.path.abspath(file_path)
    file_handler = FileOpen(abs_path)
    grid = file_handler.open()
    return grid


