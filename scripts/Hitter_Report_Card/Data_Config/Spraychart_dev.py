import warnings
from typing import Optional, List

import pandas as pd
from matplotlib import axes, pyplot as plt
from pybaseball import plot_stadium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

def spraychart_final(data: pd.DataFrame, team_stadium: str, title: str = '', tooltips: Optional[List[str]] = None,
               size: int = 100, colorby: str = 'events', legend_title: str = '', width: int = 500,
               height: int = 500) -> axes.Axes:
    """
    Produces a spraychart using statcast data overlayed on specified stadium
    """
    # Pull stadium plot to overlay hits on
    base = plot_stadium(team_stadium, title, width-50, height)

    # Only plot pitches where something happened
    sub_data = data.copy().reset_index(drop=True)
    sub_data = sub_data[sub_data['events'].notna() & sub_data['hc_x'].notna() & sub_data['hc_y'].notna()]

    # Define full color mapping for all possible event types
    event_colors = {
        'Single': '#89CFF0',  # Light Blue
        'Double': '#9370DB',  # Purple
        'Triple': '#4682B4',  # Steel Blue
        'Home Run': '#FF4500',  # Red-Orange
        'Field Out': '#FFA500',  # Orange
        'Force Out': '#DC143C',  # Crimson
        'Grounded Into Double Play': '#A9A9A9',  # Dark Gray
        'Double Play': '#8B0000',  # Dark Red
        'Field Error': '#FFD700',  # Gold
        'Fielders Choice': '#20B2AA',  # Light Sea Green
        'Fielders Choice Out': '#228B22',  # Forest Green
        'Sac Bunt': '#32CD32',  # Lime Green
        'Sac Fly': '#98FB98',  # Pale Green
    }

    if colorby == 'events':
        sub_data['event'] = sub_data['events'].str.replace('_', ' ').str.title()  # Format events consistently
        color_label = 'event'
        if not legend_title:
            legend_title = 'Outcome'
    elif colorby == 'player':
        color_label = 'player_name'
        if not legend_title:
            legend_title = 'Player'
    else:
        color_label = colorby
        if not legend_title:
            legend_title = colorby

    # Filter only the event types that actually appear in the dataset
    unique_events = sub_data[color_label].unique()
    filtered_colors = {event: event_colors[event] for event in unique_events if event in event_colors}

    # Scatter plot of hits with filtered event colors
    scatters = []
    for event, color in filtered_colors.items():
        color_sub_data = sub_data[sub_data[color_label] == event]
        if not color_sub_data.empty:
            scatter = plt.scatter(
                color_sub_data["hc_x"], color_sub_data['hc_y'].mul(-1), size, label=event, color=color, alpha=0.7
            )
            scatters.append(scatter)

    # Create custom legend (only for events that appeared)
    legend_patches = [mpatches.Patch(color=color, label=event) for event, color in filtered_colors.items()]

    # Shrink the legend, move inside plot, and adjust layout
    plt.legend(
        handles=legend_patches, title=legend_title, loc='lower right', fontsize=7, frameon=True, ncol=1,
        bbox_to_anchor=(0.95, 0.1)  # Moves legend inside the bottom-right
    )

    return base  # Keep plt.show() outside

