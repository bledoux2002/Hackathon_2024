import pandas as pd
import os
import re
import pandas as pd
import pdfplumber
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

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


def extract_shot_origin(curves, rects):

    min_x = 100
    max_x = 0

    centroids = []

    for curve in curves:
        x0, x1, y0, y1 = curve["x0"], curve["x1"], curve["y0"], curve["y1"]

        x_length = abs(x1 - x0)
        y_length = abs(y1 - y0)

        points = curve["pts"]
        area = calculate_area(x0, x1, y0, y1)

        if area < 300 and x0 < 300 and y0 < 500 and y0 > 350:
            if x0 < min_x:
                min_x = x0
                min_coords = [x0, y1]

            if x1 > max_x:
                max_x = x1
                max_coords = [x1, y1]

            if y1 < 478:
                rect = Rectangle([x0, y0], x_length, y_length)
                target = "on_target" if len(curve['pts']) == 4 else "off_target"
                goal = True if len(curve['pts']) == 5 else False
                centroids.append((rect.centroid, target, goal))
                
    for rect in rects:
        x0, x1, y0, y1 = rect["x0"], rect["x1"], rect["y0"], rect["y1"]

        x_length = x0 - x1
        y_length = y1 - y0

        area = calculate_area(x0, x1, y0, y1)

        if area < 300 and rect["x0"] < 300 and rect["y0"] < 500 and rect["y0"] > 350:
            if x0 < min_x:
                min_x = x0
                min_coords = [x0, y1]

            if x1 > max_x:
                max_x = x1
                max_coords = [x1, y1]

            if y1 < 478:
                rect = Rectangle([x0, y0], x_length, y_length)
                target = "blocked"
                goal = False
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


def parse_shot_locs(src_folder: str):
    """
    Parse shot locations from PDF files in a source folder.
    
    Args:
        src_folder (str): Path to folder containing PDF files
        team (str): Team name to process
    
    Returns:
        pandas.DataFrame: Shot location data_pos_pos_pos_pos for the specified team
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
                team_1_origins = extract_shot_origin(team_1_curves, team_1_rects)
                y_length, x_length = get_field_length(team_1_curves)

                # Calculate translation factors for normalization
                length_translation = 60 / y_length
                width_translation = 75 / x_length

                # Create DataFrame for team 1 shot positions                
                team_1_shot_origin = pd.DataFrame(
                    {
                        "team_name": team_1_name,
                        "length": [centroid[0][1] for centroid in team_1_origins],
                        "width": [centroid[0][0] for centroid in team_1_origins],
                        "target": [centroid[1] for centroid in team_1_origins],
                        "goal": [centroid[2] for centroid in team_1_origins],
                    }
                )
                # Translate shot positions to normalized coordinates
                team_1_shot_origin["length_translated"] = (
                    60 - (team_1_shot_origin["length"] - 286.74831) * length_translation
                )
                team_1_shot_origin["width_translated"] = (
                    75
                    - (team_1_shot_origin["width"] - 22.152230000000003)
                    * width_translation
                )
                team_1_shot_origin["matchdate"] = pd.to_datetime(match_date, dayfirst=True)

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
            team_2_origins = extract_shot_origin(team_2_curves, team_2_rects)
            y_length, x_length = get_field_length(team_2_curves)

            length_translation = 60 / y_length
            width_translation = 75 / x_length

            # Create DataFrame for team 2 shot origins
            team_2_shot_origin = pd.DataFrame(
                    {
                        "team_name": team_2_name,
                        "length": [centroid[0][1] for centroid in team_2_origins],
                        "width": [centroid[0][0] for centroid in team_2_origins],
                        "target": [centroid[1] for centroid in team_2_origins],
                        "goal": [centroid[2] for centroid in team_2_origins],
                    }
                )
            # Translate shot positions to normalized coordinates
            team_2_shot_origin["length_translated"] = (
                60 - (team_2_shot_origin["length"] - 286.74831) * length_translation
            )
            team_2_shot_origin["width_translated"] = (
                75 - (team_2_shot_origin["width"] - 22.152230000000003) * width_translation
            )
            team_2_shot_origin["matchdate"] = pd.to_datetime(match_date, dayfirst=True)

        # Add opponent team names
        team_1_shot_origin["opponent_team_name"] = team_2_name
        team_2_shot_origin["opponent_team_name"] = team_1_name

        # Concatenate results
        final = pd.concat([final, team_1_shot_origin, team_2_shot_origin])

    return final

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

master_df = None

for teamname, pdf_path in name_to_pdfs.items():
    curr_df = parse_shot_locs(pdf_path)
    if master_df is None:
        master_df = curr_df
        continue
    master_df = pd.concat([master_df, curr_df])

master_df.to_csv('./master_field.csv')