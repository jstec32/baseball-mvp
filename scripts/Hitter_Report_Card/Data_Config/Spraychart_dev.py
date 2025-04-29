import warnings
from typing import Optional, List

import pandas as pd
from matplotlib import axes, pyplot as plt
from pybaseball import plot_stadium
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pybaseball.plotting import transform_coordinates, STADIUM_SCALE


def spraychart_final(data: pd.DataFrame, team_stadium: str, title: str = '',
                     size: int = 100, colorby: str = 'events', legend_title: str = '',
                     width: int = 500, height: int = 500) -> axes.Axes:



    base = plot_stadium(team_stadium, title, width - 50, height)
    sub_data = data.copy().reset_index(drop=True)

    sub_data = sub_data.rename(columns={
        'hc_x': 'x',
        'hc_y': 'y'
    })

    sub_data = sub_data[sub_data['events'].notna() & sub_data['x'].notna() & sub_data['y'].notna()]


    sub_data['x'] = pd.to_numeric(sub_data['x'], errors='coerce')
    sub_data['y'] = pd.to_numeric(sub_data['y'], errors='coerce')


    event_colors = {
        'Single': '#89CFF0',
        'Double': '#9370DB',
        'Triple': '#4682B4',
        'Home Run': '#FF4500',
        'Field Out': '#FFA500',
        'Force Out': '#DC143C',
        'Grounded Into Double Play': '#A9A9A9',
        'Double Play': '#8B0000',
        'Field Error': '#FFD700',
        'Fielders Choice': '#20B2AA',
        'Fielders Choice Out': '#228B22',
        'Sac Bunt': '#32CD32',
        'Sac Fly': '#98FB98',
    }

    if colorby == 'events':
        sub_data['event'] = sub_data['events'].str.replace('_', ' ').str.title()
        color_label = 'event'
        legend_title = legend_title or 'Outcome'
    else:
        color_label = colorby
        legend_title = legend_title or colorby

    unique_events = sub_data[color_label].unique()
    filtered_colors = {event: event_colors.get(event, 'gray') for event in unique_events}

    # Scatter plot on stadium
    for event, color in filtered_colors.items():
        event_data = sub_data[sub_data[color_label] == event]
        plt.scatter(event_data['x'], -event_data['y'], s=size, label=event, color=color, alpha=0.7)


    legend_patches = [mpatches.Patch(color=color, label=event) for event, color in filtered_colors.items()]

    plt.legend(
        handles=legend_patches, title=legend_title,
        loc='lower right', fontsize=10, title_fontsize=11, frameon=True, ncol=1, bbox_to_anchor=(0.95, 0)
    )

    #plt.title(title, fontsize=14, fontweight="bold", pad=15, loc='center')


    return base


