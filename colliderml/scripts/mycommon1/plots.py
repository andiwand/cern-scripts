import matplotlib.pyplot as plt


def get_colors():
    """
    Returns a list of colors for plotting.
    """
    colors = [
        "C0",  # blue
        "C1",  # orange
        "C2",  # green
        "C3",  # red
        "C4",  # purple
        "C5",  # brown
        "C6",  # pink
        "C7",  # gray
        "C8",  # olive
        "C9",  # cyan
    ]
    return colors


def get_color(i):
    """
    Returns a color for plotting based on the index.
    """
    colors = get_colors()
    if i < 0 or i >= len(colors):
        raise ValueError(f"Index {i} is out of range for colors list.")
    return colors[i]


def get_markers():
    """
    Returns a list of markers for plotting.
    """
    markers = [
        "o",  # circle
        "s",  # square
        "^",  # triangle_up
        "v",  # triangle_down
        "D",  # diamond
        "*",  # star
        "X",  # x
        "+",  # plus
        "x",  # x
        "|",  # vertical line
        "_",  # horizontal line
    ]
    return markers


def get_marker(i):
    """
    Returns a marker for plotting based on the index.
    """
    markers = get_markers()
    if i < 0 or i >= len(markers):
        raise ValueError(f"Index {i} is out of range for markers list.")
    return markers[i]
