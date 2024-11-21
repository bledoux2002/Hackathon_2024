import os
import re
import pandas as pd
import pdfplumber
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import streamlit as st
import extract_pdf
from plotting import goal_heatmap, goal_scatter

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
    data = pd.read_csv("./master.csv") # WITHOUT DOCKER
    #data = pd.read_csv("match-reports/existing-match-reports-code/master.csv") # WITH DOCKER
    data = data.iloc[:, 1:]
    data = data.round(1)
    data = data.drop_duplicates().reset_index(drop=True)

    # IF A SINGLE TEAM IS PICKED TO ANALYZE
    if selected_home_team != "" and not selected_opponent_team:
        global_vulnerable, global_opportune = get_global_data(data, selected_home_team, is_all_shots)

        st.header(f"{selected_home_team} vs. All Opponents")
        # write_vulnerable_and_opportune(global_vulnerable, global_opportune)
        col1, col2 = st.columns(2)

        with col1:
            st.pyplot(goal_heatmap(global_vulnerable, title=f'{selected_home_team} vulnerable'))

        with col2:
            st.pyplot(goal_scatter(global_vulnerable, title=f'{selected_home_team} vulnerable'))

        col3, col4 = st.columns(2)

        with col3:
            st.pyplot(goal_heatmap(global_opportune, title=f'{selected_home_team} opportune'))

        with col4:
            st.pyplot(goal_scatter(global_opportune, title=f'{selected_home_team} opportune'))

    # IF A SECOND TEAM IS PICKED TO ANALYZE
    if selected_home_team != "" and selected_opponent_team != "" and selected_home_team != selected_opponent_team:
        local_vulnerable, local_opportune = get_local_data(data, selected_home_team, selected_opponent_team, is_all_shots)

        st.header(f"{selected_home_team} vs. {selected_opponent_team}")
        # write_vulnerable_and_opportune(local_vulnerable, local_opportune)

        col5, col6 = st.columns(2)

        with col5:
            st.pyplot(goal_heatmap(local_vulnerable, title=f'{selected_home_team} vulnerable'))

        with col6:
            st.pyplot(goal_heatmap(local_opportune, title=f'{selected_home_team} opportune'))

    
        # st.write(goal_scatter(local_vulnerable, title=f'{selected_home_team} vulnerable'))
        # st.write(goal_scatter(local_opportune, title=f'{selected_home_team} opportune'))

        # st.dataframe(local_vulnerable)
        # st.dataframe(local_opportune)

        home_goals = local_opportune['goal'].sum()
        away_goals = local_vulnerable['goal'].sum()

        st.sidebar.subheader("Score:")
        st.sidebar.write(f"{selected_home_team}: {home_goals}")
        st.sidebar.write(f"{selected_opponent_team}: {away_goals}")

    st.header("Entire Dataset")
    st.dataframe(data)