import os
import re
import pandas as pd
import pdfplumber


class Rectangle:
    def __init__(
        self, bl_coord: tuple[float, float], width: float, height: float
    ) -> None:
        self.coords = [
            list(bl_coord),
            [bl_coord[0] + width, bl_coord[1] - height],
            [bl_coord[0] + width, bl_coord[1] + height],
            [bl_coord[0], bl_coord[1] + height],
        ]
        self.centroid = [bl_coord[0] + (width / 2), bl_coord[1] + (height / 2)]
        self.width = width
        self.height = height


def get_positions(filepath):
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[1]
        page_tables = page.extract_tables()

    positions = re.findall(r"[A-Z]{2,}", page_tables[0][2][0])

    team_1_positions = positions[::2]
    team_2_positions = positions[1::2]

    position_ref = ["B", "DMF", "CM", "AM", "W", "CF"]

    team_position_groups = []

    for team in [team_1_positions, team_2_positions]:
        position_groups = {}
        for position in position_ref:
            filtered_strings = list(filter(lambda x: position in x, team[:11]))
            position_groups[position] = filtered_strings
            team_position_groups.append(position_groups)


def get_field_length(curves):
    """
    Plots the curves on a matplotlib canvas.
    """

    for curve in curves:
        if 15 < curve["x0"] < 24 and curve["y0"] < 300:
            x0, x1, y0, y1 = curve["x0"], curve["x1"], curve["y0"], curve["y1"]
            x_length = abs(x1 - x0)
            y_length = abs(y1 - y0)

    return y_length, x_length


def calculate_area(x1, x2, y1, y2):
    side_a = abs(x2 - x1)
    side_b = abs(y2 - y1)

    # Calculate the area of the rectangle
    area = side_a * side_b

    return area


def get_positions_and_names(filepath):
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[1]
        page_tables = page.extract_tables()

    positions = re.findall(r"[A-Z]{2,}", page_tables[0][2][0])
    names = re.findall(r"[A-Z]\. [A-Za-z]+", page_tables[0][2][0])

    team_1_positions = positions[::2]
    team_2_positions = positions[1::2]

    team_1_names = names[::2]
    team_2_names = names[1::2]

    team_1_starters = team_1_names[:11]
    team_1_subs = team_1_names[11 : len(team_1_positions)]

    team_2_starters = team_2_names[:11]
    team_2_subs = team_2_names[11 : len(team_2_positions)]

    return team_1_positions[:11], team_2_positions[:11]


def extract_shot_loc(curves, rects):

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
                centroids.append(rect.centroid)

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
                centroids.append(rect.centroid)
    return centroids


def initial_extraction(filepath, page_num):
    with pdfplumber.open(filepath) as pdf:
        page = pdf.pages[page_num]
        objects = page.objects
        curves = objects.get("curve", [])
        rects = objects.get("rect", [])

        page_tables = page.extract_tables()
    return curves, rects, page_tables


def get_formation(positions):
    position_groups = ["B", "DMF", "CM", "AM", "W", "CF"]

    positions_group_dict = {}

    for position in position_groups:
        filtered_strings = list(filter(lambda x: position in x, positions))
        positions_group_dict[position] = filtered_strings

    return positions_group_dict


def parse_shot_locs(src_folder: str, team: str):

    final = pd.DataFrame()
    file_names = os.listdir(src_folder)

    if not file_names:
        return None

    if ".DS_Store" in file_names:
        file_names.remove(".DS_Store")

    for file in file_names:
        team_1_positions, team_2_positions = get_positions_and_names(
            f"{src_folder}/{file}"
        )
        for i in range(11, 15):
            team_1_curves, team_1_rects, team_1_text = initial_extraction(
                f"{src_folder}/{file}", i
            )
            if "SHOTS" in team_1_text[0][0][0].split("\n"):
                team_1_name = team_1_text[0][0][0].split("\n")[0]
                match_date = re.findall(r"\((.*?)\)", team_1_text[0][0][0])[-1].replace(
                    ".", "-"
                )

                team_1_centroids = extract_shot_loc(team_1_curves, team_1_rects)
                y_length, x_length = get_field_length(team_1_curves)

                length_translation = 60 / y_length
                width_translation = 75 / x_length

                team_1_shot_pos = pd.DataFrame(
                    {
                        "team_name": team_1_name,
                        "length": [centroid[1] for centroid in team_1_centroids],
                        "width": [centroid[0] for centroid in team_1_centroids],
                    }
                )
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

        team_2_curves, team_2_rects, team_2_text = initial_extraction(
            f"{src_folder}/{file}", i + 1
        )
        if "SHOTS" in team_2_text[0][0][0].split("\n"):
            team_2_name = team_2_text[0][0][0].split("\n")[0]
            match_date = re.findall(r"\((.*?)\)", team_2_text[0][0][0])[-1].replace(
                ".", "-"
            )

            team_2_centroids = extract_shot_loc(team_2_curves, team_2_rects)
            y_length, x_length = get_field_length(team_2_curves)

            length_translation = 60 / y_length
            width_translation = 75 / x_length

            team_2_shot_pos = pd.DataFrame(
                {
                    "team_name": team_2_name,
                    "length": [centroid[1] for centroid in team_2_centroids],
                    "width": [centroid[0] for centroid in team_2_centroids],
                }
            )
            team_2_shot_pos["length_translated"] = (
                60 - (team_2_shot_pos["length"] - 286.74831) * length_translation
            )
            team_2_shot_pos["width_translated"] = (
                75 - (team_2_shot_pos["width"] - 22.152230000000003) * width_translation
            )
            team_2_shot_pos["matchdate"] = pd.to_datetime(match_date, dayfirst=True)

        team_1_shot_pos["opp_backline_num"] = len(get_formation(team_2_positions)["B"])
        team_1_shot_pos["backline_num"] = len(get_formation(team_1_positions)["B"])

        team_2_shot_pos["opp_backline_num"] = len(get_formation(team_1_positions)["B"])
        team_2_shot_pos["backline_num"] = len(get_formation(team_2_positions)["B"])

        team_1_shot_pos["opponent_team_name"] = team_2_name
        team_2_shot_pos["opponent_team_name"] = team_1_name

        final = pd.concat([final, team_1_shot_pos, team_2_shot_pos])

    return final