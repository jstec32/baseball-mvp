# visualization_config.py
import matplotlib.pyplot as plt

def apply_global_styles():
    """
    Apply global Matplotlib styles for font sizes and families.
    """
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 12,  # Default font size
        'axes.titlesize': 14,  # Title font size
        'axes.labelsize': 12,  # Axis label size
        'legend.fontsize': 10,  # Legend font size
        'xtick.labelsize': 10,  # X-axis tick label size
        'ytick.labelsize': 10,  # Y-axis tick label size
        'figure.titlesize': 16,  # Figure title font size
        'figure.titleweight': 'bold',  # Bold titles
    })
