import os
import re
import pandas as pd
import pdfplumber
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import streamlit as st
import extract_pdf

def plot_shots(data):
  home_team = teamname
  teams = data['team_name'].unique()
  opponents = [team for team in teams if team != home_team]
  x = np.array(data['width'])
  y = np.array(data['length'])
  target = np.array(data['target'])
  goal = np.array(data['goal'])

  goalX = [85, 85, 510, 510]
  goalY = [600, 740, 740, 600]

  fig, axes = plt.subplots(len(opponents), 2, figsize=(13, len(opponents) * 3))

  for i in range (len(axes)):
      # Home mask = only shots taken by teams on opposition goal
      home_mask = data['team_name'] == home_team
      opp_mask = data['opponent_team_name'] == opponents[i]
      x_home = x[home_mask & opp_mask]
      y_home = y[home_mask & opp_mask]
      target_home = target[home_mask & opp_mask]
      goal_home = goal[home_mask & opp_mask]

      for j in range(len(x_home)):
          marker = 'D' if goal_home[j] else 'o'
          color = 'b' if target_home[j] == "off_target" else 'r'
          axes[i, 0].scatter(x_home[j], y_home[j], marker=marker, color=color)
      axes[i, 0].set_title(f'{home_team} shots on {opponents[i]}')
      
      axes[i, 0].plot(goalX, goalY, color='purple')
      axes[i, 0].set_xlim(0, 595)
      axes[i, 0].set_ylim(600, 800)
      axes[i, 0].set_aspect('equal', adjustable='box')

      # Opp mask = only shots taken by the opponents on home goal
      opp_mask = data['team_name'] == opponents[i]
      home_mask = data['opponent_team_name'] == home_team
      x_opp = x[opp_mask & home_mask]
      y_opp = y[opp_mask & home_mask]
      target_opp = target[opp_mask & home_mask]
      goal_opp = goal[opp_mask & home_mask]

      for j in range(len(x_opp)):
          marker = 'D' if goal_opp[j] else 'o'
          color = 'b' if target_opp[j] == "off_target" else 'r'
          axes[i, 1].scatter(x_opp[j], y_opp[j], marker=marker, color=color)
      axes[i, 1].set_title(f'{opponents[i]} shots on {home_team}')
      
      axes[i, 1].plot(goalX, goalY, color='purple')
      axes[i, 1].set_xlim(0, 595)
      axes[i, 1].set_ylim(600, 800)
      axes[i, 1].set_aspect('equal', adjustable='box')
  st.write(fig)

def plot_kde(data):
    x = np.array(data['width'])
    y = np.array(data['length'])

    dataNew = np.vstack([x, y])

    nbins = 20

    k = gaussian_kde(dataNew, bw_method=0.4)

    goalX = [85, 85, 510, 510]
    goalY = [600, 740, 740, 600]

    fig, ax = plt.subplots(figsize=(6, 3))  
    ax.set_title('2D Density with shading')

    xi, yi = np.mgrid[0:595:nbins*1j, 600:800:nbins*1j]
    zi = k(np.vstack([xi.flatten(), yi.flatten()]))

    ax.pcolormesh(xi, yi, zi.reshape(xi.shape), shading='gouraud', cmap='inferno')

    ax.plot(goalX, goalY, color='white')

    ax.set_xlim(0, 595)
    ax.set_ylim(600, 800)
    ax.set_aspect('equal', adjustable='box')

    st.pyplot(fig)

def get_global_data(data_copy, selected_home_team, is_all_shots):
    """
    Parameters
    ---------
    data_copy[pd.DataFrame]: data
    selected_home_team[str]: String of the team to analyze
    is_all_shots[bool]: True if user wants to see all shots, otherwise only shows goals

    Returns
    -------
    The vulnerabilities and opportunities of the selected team 
    against all other opponents.  
    """
    if not is_all_shots:
        data_copy = data_copy.loc[data_copy['goal'] == True]
    vulnerable = data_copy.loc[data_copy['opponent_team_name'] == selected_home_team]
    opportune = data_copy.loc[data_copy['team_name'] == selected_home_team]
    return vulnerable, opportune

def get_local_data(data_copy, selected_home_team, selected_opponent_team, is_all_shots):
    """
    Parameters
    ---------
    data_copy[pd.DataFrame]: data
    selected_home_team[str]: String of the team to analyze
    selected_opponent_team[str]: String of the opponent
    is_all_shots[bool]: True if user wants to see all shots, otherwise only shows goals

    Returns
    -------
    The vulnerabilities and opportunities of the selected team 
    against the specified opponent.
    """
    if not is_all_shots:
        data_copy = data_copy.loc[data_copy['goal'] == True]
    vulnerable = data_copy.loc[(data_copy['opponent_team_name'] == selected_home_team) & (data_copy['team_name'] == selected_opponent_team)]
    opportune = data_copy.loc[(data_copy['team_name'] == selected_home_team) & (data_copy['opponent_team_name'] == selected_opponent_team)]
    return vulnerable, opportune

def write_vulnerable_and_opportune(vulnerable, opportune):
    st.subheader(f"Vulnerabilities for {selected_home_team}")
    st.dataframe(vulnerable)

    st.subheader(f"Opportunities for {selected_home_team}")
    st.dataframe(opportune)

if __name__ == "__main__":
    name_to_pdfs = {
        "":"",
        "Northwestern Wildcats": f"../northwestern-2024",
        "Washington Huskies": f"../washington-2024/",
        "Indiana Hoosiers": f"../indiana-2024/",
        "Maryland College Park Terrapins": f"../maryland-2024/",
        "Michigan State Spartans": f"../mich-state-2024/",
        "Michigan Wolverines": f"../michigan-2024/",
        "Ohio State Buckeyes": f"../ohio-st-2024/",
        "Penn State Nittany Lion": f"../penn-state-2024/",
        "Rutgers Scarlet Knights": f"../rutgers-2024/",
        "UCLA Bruins": f"../ucla-2024/"
    }

    # SIDEBAR
    st.sidebar.header("Filter:")
    selected_home_team = st.sidebar.selectbox("Select team to analyze", name_to_pdfs.keys(), key=0)
    selected_opponent_team = st.sidebar.selectbox("[OPTIONAL] Select opponent", name_to_pdfs.keys(), key=1)
    is_all_shots = st.sidebar.toggle("Only Goals / All Shots")

    # GETTING THE DATA
    data = pd.read_csv("./master.csv")
    data = data.iloc[:, 1:]
    data = data.round(1)
    data = data.drop_duplicates().reset_index(drop=True)
    st.header("Entire Dataset")
    st.dataframe(data)

    # IF A SINGLE TEAM IS PICKED TO ANALYZE
    if selected_home_team != "" and not selected_opponent_team:
        global_vulnerable, global_opportune = get_global_data(data, selected_home_team, is_all_shots)

        st.header(f"{selected_home_team} vs. All Opponents")
        write_vulnerable_and_opportune(global_vulnerable, global_opportune)

    # IF A SECOND TEAM IS PICKED TO ANALYZE
    if selected_home_team != "" and selected_opponent_team != "":
        local_vulnerable, local_opportune = get_local_data(data, selected_home_team, selected_opponent_team, is_all_shots)

        st.header(f"{selected_home_team} vs. {selected_opponent_team}")
        write_vulnerable_and_opportune(local_vulnerable, local_opportune)

        home_goals = local_opportune['goal'].sum()
        away_goals = local_vulnerable['goal'].sum()

        st.sidebar.subheader("Score:")
        st.sidebar.write(f"{selected_home_team}: {home_goals}")
        st.sidebar.write(f"{selected_opponent_team}: {away_goals}")