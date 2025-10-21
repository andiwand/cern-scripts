import numpy as np


def ratio_std(x, y, std_x, std_y):
    """
    Calculate the standard deviation of the ratio of two variables x/y.
    
    Parameters:
    x (float): The first variable.
    y (float): The second variable.
    std_x (float): The standard deviation of the first variable.
    std_y (float): The standard deviation of the second variable.
    
    Returns:
    float: The standard deviation of the ratio x/y.
    """
    return np.sqrt(
        (std_x / y) ** 2 + (std_y * x / y**2) ** 2
    )
