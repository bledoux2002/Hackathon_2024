import os
import re
import pandas as pd
import pdfplumber
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
import streamlit as st

pts = []

class Rectangle:
    """
    A class to represent a rectangular area with coordinates and dimensions.
    
    Attributes:
        coords (list): Four corner coordinates of the rectangle
        centroid (list): Coordinates of the rectangle's center point
        width (float): Width of the rectangle
        height (float): Height of the rectangle
    """
    def __init__(
        self, bl_coord: tuple[float, float], width: float, height: float
    ) -> None:
        """
        Initialize a Rectangle object.
        
        Args:
            bl_coord (tuple): Bottom-left coordinate (x, y)
            width (float): Width of the rectangle
            height (float): Height of the rectangle
        """
        # Calculate rectangle coordinates based on bottom-left point
        self.coords = [
            list(bl_coord),  # Bottom-left point
            [bl_coord[0] + width, bl_coord[1] - height],  # Bottom-right point
            [bl_coord[0] + width, bl_coord[1] + height],  # Top-right point
            [bl_coord[0], bl_coord[1] + height],  # Top-left point
        ]
        # Calculate rectangle's center point
        self.centroid = [bl_coord[0] + (width / 2), bl_coord[1] + (height / 2)]
        
        self.width = width
        self.height = height


def get_positions(filepath):
    """
    Extract player positions from a PDF file.
    
    Args:
        filepath (str): Path to the PDF file
    
    Returns:
        List of position groups for both teams
    """
    # Open the PDF and extract tables from the second page
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[1]
        page_tables = page.extract_tables()

    # Extract position strings using regex
    positions = re.findall(r"[A-Z]{2,}", page_tables[0][2][0])

    # Split positions into two teams
    team_1_positions = positions[::2]
    team_2_positions = positions[1::2]

    # Reference list of standard positions
    position_ref = ["B", "DMF", "CM", "AM", "W", "CF"]

    team_position_groups = []

    # Group positions for each team
    for team in [team_1_positions, team_2_positions]:
        position_groups = {}
        for position in position_ref:
            # Filter positions that match each reference position
            filtered_strings = list(filter(lambda x: position in x, team[:11]))
            position_groups[position] = filtered_strings
            team_position_groups.append(position_groups)


def get_field_length(curves):
    """
    Calculate the length and width of the field based on curve coordinates.
    
    Args:
        curves (list): List of curve objects from PDF
    
    Returns:
        tuple: Y-length and X-length of the field
    """
    # Iterate through curves to find field boundaries
    for curve in curves:
        # Check if curve is within expected field coordinates
        if 15 < curve["x0"] < 24 and curve["y0"] < 300:
            x0, x1, y0, y1 = curve["x0"], curve["x1"], curve["y0"], curve["y1"]
            # Calculate absolute lengths
            x_length = abs(x1 - x0)
            y_length = abs(y1 - y0)

    return y_length, x_length


def calculate_area(x1, x2, y1, y2):
    """
    Calculate the area of a rectangle.
    
    Args:
        x1 (float): X-coordinate of first point
        x2 (float): X-coordinate of second point
        y1 (float): Y-coordinate of first point
        y2 (float): Y-coordinate of second point
    
    Returns:
        float: Area of the rectangle
    """
    # Calculate side lengths using absolute differences
    side_a = abs(x2 - x1)
    side_b = abs(y2 - y1)

    # Calculate rectangle area
    area = side_a * side_b

    return area


def get_positions_and_names(filepath):
    """
    Extract player positions and names from a PDF file.
    
    Args:
        filepath (str): Path to the PDF file
    
    Returns:
        tuple: Positions for the first 11 players of each team
    """
    # Open PDF and extract tables from second page
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[1]
        page_tables = page.extract_tables()

    # Extract positions and names using regex
    positions = re.findall(r"[A-Z]{2,}", page_tables[0][2][0])
    names = re.findall(r"[A-Z]\. [A-Za-z]+", page_tables[0][2][0])

    # Split positions and names into teams
    team_1_positions = positions[::2]
    team_2_positions = positions[1::2]

    team_1_names = names[::2]
    team_2_names = names[1::2]

    # Separate starters and substitutes
    team_1_starters = team_1_names[:11]
    team_1_subs = team_1_names[11 : len(team_1_positions)]

    team_2_starters = team_2_names[:11]
    team_2_subs = team_2_names[11 : len(team_2_positions)]

    return team_1_positions[:11], team_2_positions[:11]


def extract_shot_loc(curves, rects):
    """
    Extract shot locations from curves and rectangles.
    
    Args:
        curves (list): List of curve objects
        rects (list): List of rectangle objects
    
    Returns:
        list: Centroids of shot locations
    """
    # Initialize tracking variables for shot boundaries
    min_x = 100
    max_x = 0

    centroids = []

    # lower_threshold = 8
    upper_threshold = 100
    goal_pt_count = 5
    save_pt_count = 9
    # Process curves to find shot locations
    
    for curve in curves:
        if len(curve['pts']) > upper_threshold or len(curve['pts']) == 6:
            continue
        pts.append(len(curve['pts']))
        x0, x1, y0, y1 = curve["x0"], curve["x1"], curve["y0"], curve["y1"]

        x_length = abs(x1 - x0)
        y_length = abs(y1 - y0)

        points = curve["pts"]
        area = calculate_area(x0, x1, y0, y1)

        # Filter for potential shot locations based on area and position
        if area < 300 and y0 < 790 and y0 > 600:
            # Track minimum and maximum x coordinates
            if x0 < min_x:
                min_x = x0
                min_coords = [x0, y1]

            if x1 > max_x:
                max_x = x1
                max_coords = [x1, y1]

            rect = Rectangle([x0, y0], x_length, y_length)
            
            # Determine if shot was on or off target, saved or went in
            target = "on_target" if rect.centroid[0] > 85 and rect.centroid[0] < 510 and rect.centroid[1] > 600 and rect.centroid[1] < 740 else "off_target"
            goal = True if len(curve['pts']) == 5 else False

            centroids.append((rect.centroid, target, goal))



    # Repeat similar process for rectangles
    for rect in rects:
        x0, x1, y0, y1 = rect["x0"], rect["x1"], rect["y0"], rect["y1"]

        x_length = x0 - x1
        y_length = y1 - y0

        area = calculate_area(x0, x1, y0, y1)

        # Similar filtering as with curves
        if area < 300 and rect["y0"] < 790 and rect["y0"] > 600:
            if x0 < min_x:
                min_x = x0
                min_coords = [x0, y1]

            if x1 > max_x:
                max_x = x1
                max_coords = [x1, y1]

            # Determine if shot was on or off target (might be useless)
            target = "on_target" if rect.centroid[0] > 85 and rect.centroid[0] < 510 and rect.centroid[1] > 600 and rect.centroid[1] < 740 else "off_target"
            goal = True if len(curve['pts']) == 5 else False

            centroids.append((rect.centroid, target, goal))
    
    return centroids


def initial_extraction(filepath, page_num):
    """
    Extract initial data from a specific page of a PDF.
    
    Args:
        filepath (str): Path to the PDF file
        page_num (int): Page number to extract data from
    
    Returns:
        tuple: Curves, rectangles, and page tables
    """
    # Open PDF and extract specific page objects and tables
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[page_num]
        objects = page.objects
        curves = objects.get("curve", [])
        rects = objects.get("rect", [])

        page_tables = page.extract_tables()
    
    return curves, rects, page_tables


def get_formation(positions):
    """
    Group player positions into predefined categories.
    
    Args:
        positions (list): List of player positions
    
    Returns:
        dict: Dictionary of positions grouped by categories
    """
    # List of position groups to categorize players
    position_groups = ["B", "DMF", "CM", "AM", "W", "CF"]

    positions_group_dict = {}

    # Filter and group positions
    for position in position_groups:
        filtered_strings = list(filter(lambda x: position in x, positions))
        positions_group_dict[position] = filtered_strings

    return positions_group_dict


def parse_shot_locs(src_folder: str, team: str):
    """
    Parse shot locations from PDF files in a source folder.
    
    Args:
        src_folder (str): Path to folder containing PDF files
        team (str): Team name to process
    
    Returns:
        pandas.DataFrame: Shot location data for the specified team
    """
    # Initialize final DataFrame to store results
    final = pd.DataFrame()
    file_names = os.listdir(src_folder)

    # Handle empty folder or system files
    if not file_names:
        return None

    if ".DS_Store" in file_names:
        file_names.remove(".DS_Store")

    # Process each file in the source folder
    for file in file_names:
        # Extract positions for both teams
        team_1_positions, team_2_positions = get_positions_and_names(
            f"{src_folder}/{file}"
        )
        
        # Iterate through pages to find shot data
        for i in range(11, 15):
            # Extract data for team 1
            team_1_curves, team_1_rects, team_1_text = initial_extraction(
                f"{src_folder}/{file}", i
            )
            
            # Check if current page contains shot data
            if "SHOTS" in team_1_text[0][0][0].split("\n"):
                team_1_name = team_1_text[0][0][0].split("\n")[0]
                match_date = re.findall(r"\((.*?)\)", team_1_text[0][0][0])[-1].replace(
                    ".", "-"
                )

                # Extract shot locations and field dimensions
                team_1_centroids = extract_shot_loc(team_1_curves, team_1_rects)
                y_length, x_length = get_field_length(team_1_curves)

                # Calculate translation factors for normalization
                length_translation = 60 / y_length
                width_translation = 75 / x_length

                # Create DataFrame for team 1 shot positions
                team_1_shot_pos = pd.DataFrame(
                    {
                        "team_name": team_1_name,
                        "length": [centroid[0][1] for centroid in team_1_centroids],
                        "width": [centroid[0][0] for centroid in team_1_centroids],
                        "target": [centroid[1] for centroid in team_1_centroids],
                        "goal": [centroid[2] for centroid in team_1_centroids],
                    }
                )
                # Translate shot positions to normalized coordinates
                team_1_shot_pos["length_translated"] = (
                    60 - (team_1_shot_pos["length"] - 286.74831) * length_translation
                )
                team_1_shot_pos["width_translated"] = (
                    75
                    - (team_1_shot_pos["width"] - 22.152230000000003)
                    * width_translation
                )
                team_1_shot_pos["matchdate"] = pd.to_datetime(match_date, dayfirst=True)

                break

        # Repeat similar process for team 2
        team_2_curves, team_2_rects, team_2_text = initial_extraction(
            f"{src_folder}/{file}", i + 1
        )
        
        # Check if current page contains shot data for team 2
        if "SHOTS" in team_2_text[0][0][0].split("\n"):
            team_2_name = team_2_text[0][0][0].split("\n")[0]
            match_date = re.findall(r"\((.*?)\)", team_2_text[0][0][0])[-1].replace(
                ".", "-"
            )

            # Extract shot locations and field dimensions
            team_2_centroids = extract_shot_loc(team_2_curves, team_2_rects)
            y_length, x_length = get_field_length(team_2_curves)

            length_translation = 60 / y_length
            width_translation = 75 / x_length

            # Create DataFrame for team 2 shot positions
            team_2_shot_pos = pd.DataFrame(
                {
                    "team_name": team_2_name,
                    "length": [centroid[0][1] for centroid in team_2_centroids],
                    "width": [centroid[0][0] for centroid in team_2_centroids],
                    "target": [centroid[1] for centroid in team_2_centroids],
                    "goal": [centroid[2] for centroid in team_2_centroids],
                }
            )
            # Translate shot positions to normalized coordinates
            team_2_shot_pos["length_translated"] = (
                60 - (team_2_shot_pos["length"] - 286.74831) * length_translation
            )
            team_2_shot_pos["width_translated"] = (
                75 - (team_2_shot_pos["width"] - 22.152230000000003) * width_translation
            )
            team_2_shot_pos["matchdate"] = pd.to_datetime(match_date, dayfirst=True)

        # Add opponent and defensive line information
        team_1_shot_pos["opp_backline_num"] = len(get_formation(team_2_positions)["B"])
        team_1_shot_pos["backline_num"] = len(get_formation(team_1_positions)["B"])

        team_2_shot_pos["opp_backline_num"] = len(get_formation(team_1_positions)["B"])
        team_2_shot_pos["backline_num"] = len(get_formation(team_2_positions)["B"])

        # Add opponent team names
        team_1_shot_pos["opponent_team_name"] = team_2_name
        team_2_shot_pos["opponent_team_name"] = team_1_name

        # Concatenate results
        final = pd.concat([final, team_1_shot_pos, team_2_shot_pos])

    return final

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




if __name__ == "__main__":
  name_to_pdfs = {
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

  selected_team = st.selectbox("Select team to analyze", name_to_pdfs.keys())

  if st.button("Submit"):
      teamname = selected_team
      pdf_path = name_to_pdfs[teamname]
      data = parse_shot_locs(pdf_path, teamname)

      data = data.round(1)
      data = data.drop_duplicates().reset_index(drop=True)
      data.shape

      plot_shots(data)
      plot_kde(data)
  