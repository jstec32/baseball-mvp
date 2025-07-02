

from scripts.Scouting_Report_Template_Configuration.ChatGPT_model_prep.Pitcher_Heatmap_Data import get_db_connection

import matplotlib
matplotlib.use("Agg") 
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from matplotlib.patches import Rectangle
import seaborn as sns
import matplotlib.patches as mpatches


def fetch_hitter_data_with_pitches(hitter_id):

    query = f"""
    SELECT 
        pd.game_id,
        pd.zone,
        pd.plate_x,
        pd.plate_z,
        pd.pitch_type,
        pd.description,
        pd.events,
        CASE 
            WHEN pd.events IN ('single', 'double', 'triple', 'home_run') THEN TRUE 
            ELSE FALSE 
        END AS is_hit
    FROM pitch_data pd
    WHERE pd.batter_id = '{hitter_id}' -- Specify the hitter ID
    ORDER BY pd.zone, pd.pitch_type;
    """
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        print(f"Error fetching hitter data: {e}")
        return None
    finally:
        connection.close()

def draw_sz(sz_top=3.5, sz_bot=1.5, ls='k-'):
    plt.plot([-0.708, 0.708], [sz_bot, sz_bot], ls)
    plt.plot([-0.708, -0.708], [sz_bot, sz_top], ls)
    plt.plot([0.708, 0.708], [sz_bot, sz_top], ls)
    plt.plot([-0.708, 0.708], [sz_top, sz_top], ls)

def draw_home_plate(catcher_perspective=True, ls='k-'):
    if catcher_perspective:
        plt.plot([-0.708, 0.708], [0, 0], ls)
        plt.plot([-0.708, -0.708], [0, -0.3], ls)
        plt.plot([0.708, 0.708], [0, -0.3], ls)
        plt.plot([-0.708, 0], [-0.3, -0.6], ls)
        plt.plot([0.708, 0], [-0.3, -0.6], ls)
    else:
        plt.plot([-0.708, 0.708], [0, 0], ls)
        plt.plot([-0.708, -0.708], [0, 0.1], ls)
        plt.plot([0.708, 0.708], [0, 0.1], ls)
        plt.plot([-0.708, 0], [0.1, 0.3], ls)
        plt.plot([0.708, 0], [0.1, 0.3], ls)

def draw_attack_zones():
    plt.plot([-0.558, 0.558], [1.833, 1.833], color=(227/255, 150/255, 255/255), ls='-', lw=3)
    plt.plot([-0.558, -0.558], [1.833, 3.166], color=(227/255, 150/255, 255/255), ls='-', lw=3)
    plt.plot([0.558, 0.558], [1.833, 3.166], color=(227/255, 150/255, 255/255), ls='-', lw=3)
    plt.plot([-0.558, 0.558], [3.166, 3.166], color=(227/255, 150/255, 255/255), ls='-', lw=3)

    plt.plot([-1.108, 1.108], [1.166, 1.166], color=(255/255, 197/255, 150/255), ls='-', lw=3)
    plt.plot([-1.108, -1.108], [1.166, 3.833], color=(255/255, 197/255, 150/255), ls='-', lw=3)
    plt.plot([1.108, 1.108], [1.166, 3.833], color=(255/255, 197/255, 150/255), ls='-', lw=3)
    plt.plot([-1.108, 1.108], [3.833, 3.833], color=(255/255, 197/255, 150/255), ls='-', lw=3)

    plt.plot([-1.666, 1.666], [0.5, 0.5], color=(209/255, 209/255, 209/255), ls='-', lw=3)
    plt.plot([-1.666, -1.666], [0.5, 4.5], color=(209/255, 209/255, 209/255), ls='-', lw=3)
    plt.plot([1.666, 1.666], [0.5, 4.5], color=(209/255, 209/255, 209/255), ls='-', lw=3)
    plt.plot([-1.666, 1.666], [4.5, 4.5], color=(209/255, 209/255, 209/255), ls='-', lw=3)




def generate_hitter_heatmap(hitter_id, hitter_name, game_id):



    hitter_data = fetch_hitter_data_with_pitches(hitter_id)

    if hitter_data is None or hitter_data.empty:
        print(f"No hitter data available for {hitter_name}.")
        return None

    hitter_data = hitter_data.dropna(subset=["plate_x", "plate_z"])
    hitter_data['plot_event'] = hitter_data['events'].fillna(hitter_data['description'])
    if hitter_data.empty:
        print(f"No valid data for hitter {hitter_name}.")
        return None


    weights = hitter_data['is_hit'].astype(int)
    if weights.sum() > 0:
        weights = weights / weights.sum()
    else:
        print(f"No hits found for {hitter_name}, skipping heatmap generation.")
        return None


    game_pitches = hitter_data[hitter_data["game_id"] == game_id]
    print(game_pitches)
    EVENT_COLORS = {
        'single': 'limegreen',
        'double': 'dodgerblue',
        'triple': 'orange',
        'home_run': 'red',
        'called_strike': 'black',
        'swinging_strike': 'darkred',
        'foul': 'gray',
        'ball': 'skyblue',
        'hit_by_pitch': 'pink',
        'intent_ball': 'mediumorchid',
        'foul_tip': 'darkorange',
        'bunt_foul': 'gold',
        'missed_bunt': 'darkgoldenrod',
        'foul_bunt': 'burlywood',
        'pitchout': 'navy',
        'caught_stealing_2b': 'slategray',
        'caught_stealing_3b': 'teal',
        'caught_stealing_home': 'darkcyan',
        'pickoff_1b': 'mediumseagreen',
        'pickoff_2b': 'seagreen',
        'pickoff_3b': 'mediumaquamarine',
        'balk': 'indianred',
        'wild_pitch': 'tomato',
        'passed_ball': 'rosybrown',
        'other_out': 'dimgray',
        'strikeout': 'crimson',
        'strikeout_double_play': 'maroon',
        'grounded_into_double_play': 'chocolate',
        'force_out': 'darkkhaki',
        'fielders_choice': 'tan',
        'field_error': 'lightcoral',
        'sac_bunt': 'darkslategray',
        'sac_fly': 'lightseagreen',
        'runner_advance': 'darkturquoise',
        'runner_double_play': 'cadetblue',
        'interference': 'mediumvioletred',
        'fan_interference': 'purple',
        'field_interference': 'plum',
        'game_advisory': 'lightsteelblue',
        'game_delay': 'lavender',
        'ejection': 'firebrick',
        'review': 'darkslateblue',
        'manager_challenge': 'rebeccapurple',
        'umpire_challenge': 'mediumslateblue',
        'runner_challenge': 'slateblue',
        'batter_challenge': 'blueviolet',
        'pitching_substitution': 'darkgreen',
        'defensive_substitution': 'forestgreen',
        'offensive_substitution': 'mediumspringgreen',
        'injury': 'lightpink',
        'inning_break': 'silver'
    }
    fallback_colors = sns.color_palette("husl", 50).as_hex()
    unique_plot_events = hitter_data["plot_event"].unique()
    event_color_map = {}
    for idx, event in enumerate(unique_plot_events):
        if event in EVENT_COLORS:
            event_color_map[event] = EVENT_COLORS[event]
        else:
            # Assign unused fallback color, cycling if necessary
            event_color_map[event] = fallback_colors[idx % len(fallback_colors)]


    # Create figure
    fig, ax = plt.subplots(figsize=(4, 4))



    try:
        sns.kdeplot(
            x=hitter_data['plate_x'],
            y=hitter_data['plate_z'],
            cmap='Reds',
            fill=True,
            alpha=0.7,
            ax=ax,
            weights=hitter_data['is_hit'].astype(int)  # Weighted by hits
        )
    except Exception as e:
        print(f"Error generating hitter heatmap: {e}")
        return None


    hit_data = game_pitches[game_pitches["is_hit"]]
    miss_data = game_pitches[~game_pitches["is_hit"]]


    for event, color in event_color_map.items():
        event_data = game_pitches[game_pitches["plot_event"] == event]
        ax.scatter(
            event_data['plate_x'],
            event_data['plate_z'],
            color=color,
            edgecolors="black",
            linewidth=0.6,
            s=70,
            alpha=0.85,
            label=event  # Each pitch type could appear in the legend
        )


    # Draw the home plate, strike zone, and attack zones
    draw_home_plate()
    draw_sz()




    ax.set_xlim(-2.0, 2.0)
    ax.set_ylim(-1.0, 5.0)

    #ax.set_title(f"Hitter Heatmap - {hitter_name} (Game {game_id})", fontsize=14,fontweight="bold")

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_frame_on(False)
    ax.axis('off')


    unique_events_in_game = game_pitches["plot_event"].unique()
    legend_patches = [
        mpatches.Patch(color=event_color_map[event], label=event.replace("_", " ").title())
        for event in unique_events_in_game
    ]


    ax.legend(
        handles=legend_patches,
        title="Event Legend",
        loc='lower right',
        fontsize=6,
        frameon=True,
        ncol=1,
        bbox_to_anchor=(1.15, 0)
    )
    plt.subplots_adjust(left=0.15, right=0.85, top=0.85, bottom=0.15)

    print(f"Hitter heatmap generated for {hitter_name} in Game {game_id}.")

    return fig
