# visualization_config.py
import matplotlib.pyplot as plt

def apply_global_styles():
    """
    Apply global Matplotlib styles for font sizes and families.
    """
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial'],  # Use a consistent font across all visualizations
        'font.size': 12,               # Base font size for all text
        'axes.titlesize': 14,          # Title font size
        'axes.labelsize': 12,          # Axis label font size
        'legend.fontsize': 10,         # Legend font size
        'xtick.labelsize': 10,         # X-axis tick label font size
        'ytick.labelsize': 10,         # Y-axis tick label font size
    })
