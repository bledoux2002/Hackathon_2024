import io
import re
from typing import Sequence
from . globals import COLNAMES_KEY
import pdfplumber
import os
import pandas as pd


def extract_tables_from_pdf(pdf_path, page_number=5):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]  # page_number starts from 1
        page_tables = page.extract_tables()
    return page_tables


def split_strings_into_lists(table):
    master = []

    for i in table:
        combine_words = []
        words_acc = 0

        # Split the string based on the regex, remove empty splits and strip each
        parsed = [
            val.strip()
            for val in re.split(
                r"\s+([a-zA-Z]+)|\s+(\([^)]+\))|\s+\((?:\w+\s*\d*\s*)+\)", i
            )
            if val
        ]

        for string in parsed:
            # Check if string contains digits
            if re.search(r"\d+", string):
                if words_acc > 1:
                    combined_string = " ".join(combine_words)
                    idx = parsed.index(string) - len(combine_words)
                    parsed = (
                        parsed[:idx]
                        + [combined_string]
                        + parsed[idx + len(combine_words) :]
                    )
                    combine_words = []
                    words_acc = 0

                # Split by spaces and check for fractions
                numbers = re.split(r"\s+", string)
                split_numbers = []
                for num in numbers:
                    if re.search(r"\d/\d", num):
                        split_numbers.extend(re.split(r"/", num))
                    else:
                        split_numbers.append(num)

                idx = parsed.index(string)
                parsed = parsed[:idx] + split_numbers + parsed[idx + 1 :]
            else:
                combine_words.append(string)
                words_acc += 1

        # if any parsed items are numbers then add to master
        if any(is_number(char) for char in parsed):
            master.append(parsed)

    for idx, sublist in enumerate(master):
        for char in sublist:
            if len(char) < 7:
                if char == "%":
                    master[idx][master[idx].index(char)] = ""
                elif ("(" in char or ")" in char) and not percent_check(char):
                    master[idx][master[idx].index(char)] = ""
        master[idx] = [val for val in master[idx] if val != ""]
    return master


def is_number(num):
    """Returns True if string is a number."""
    try:
        float(num)
        return True
    except ValueError:
        return False


def percent_check(string):
    return string[0].isdigit() and string[-1] == "%"


def split_list(lst):
    idx = 1
    is_prev_val_num = is_number(lst[0]) or percent_check(lst[0])
    for string in lst[1:]:
        if bool(re.search(r"[a-zA-Z]", string)):
            if is_prev_val_num:
                return [lst[:idx], lst[idx:]]
        is_prev_val_num = is_number(string) or percent_check(string)
        idx += 1
    return [lst]


def create_team_dicts(table, comp):

    team_names = re.split(r"\d\s+", table[0][0][0].split("\n")[1])
    team_1_name = team_names[0].replace("TEAM STATS ", "").strip()
    team_2_name = team_names[-1].strip()

    match_date = re.search(r"\((.*?)\)", table[0][0][0]).group(1).replace(".", "-")

    team_1_dict = {
        "team_name": team_1_name,
        "opponent_team_name": team_2_name,
        "match_date": match_date,
        "competition": comp,
    }
    team_2_dict = {
        "team_name": team_2_name,
        "opponent_team_name": team_1_name,
        "match_date": match_date,
        "competition": comp,
    }
    for team_dict in [team_1_dict, team_2_dict]:
        for vals in COLNAMES_KEY.values():
            if isinstance(vals, list):
                for val in vals:
                    team_dict[val] = 0
            else:
                team_dict[vals] = 0
    return team_1_dict, team_2_dict


def assign_strings_to_columns(
    team: dict[str, list[str] | str | int], values: list[str], columns: Sequence[str]
) -> None:
    if values[1] == "0" and not any(percent_check(val) for val in values):
        for name in columns:
            team[name] = 0
    else:
        for idx, string in enumerate(values):
            team[columns[idx]] = string


def parse_reports(file: io.BytesIO | str) -> pd.DataFrame:

    team_stats = extract_tables_from_pdf(file)
    home_page = extract_tables_from_pdf(file, page_number=1)
    comp = home_page[0][1][0].split("\n")[-1].split(". ")[-1]
    team_1, team_2 = create_team_dicts(team_stats, comp)
    master = split_strings_into_lists(team_stats[0][1][0].split("\n"))

    split_strings_list = []
    for line in master:
        results = split_list(line)
        for result in results:
            split_strings_list.append(result)

    for line in split_strings_list:
        if line[0] in COLNAMES_KEY.keys() and len(line) > 3:
            split_idx = len(COLNAMES_KEY[line[0]])
            colnames = COLNAMES_KEY[line[0]]
            if not any(percent_check(val) for val in line):
                for idx, string in enumerate(line[1:]):
                    if idx < split_idx:
                        team_1[colnames[idx]] = string
                    else:
                        team_2[colnames[idx - split_idx]] = string
            else:
                assign_strings_to_columns(team_1, line[1 : split_idx + 1], colnames)
                assign_strings_to_columns(team_2, line[-split_idx:], colnames)

        elif line[0] in COLNAMES_KEY.keys() and len(line) == 3:
            if (
                line[1] == "0"
                and line[2] == "0"
                and isinstance(COLNAMES_KEY[line[0]], list)
            ):
                for key in COLNAMES_KEY[line[0]]:
                    team_1[key] = 0
                    team_2[key] = 0
            else:
                team_1[COLNAMES_KEY[line[0]]] = line[1]
                team_2[COLNAMES_KEY[line[0]]] = line[2]
        if "Dribbles" in line[0]:
            break

    final = pd.DataFrame([team_1, team_2])
    mask = final.apply(lambda row: row.astype(str).str.endswith("%").any(), axis=1)
    final.loc[mask] = final.loc[mask].astype(str).replace("%", "", regex=True)

    for col in final.columns:
        try:
            final[col] = pd.to_numeric(final[col])
        except:
            continue

    final = final.drop(columns=["x", "G"], errors="ignore")

    return final


def parse_from_pdf():
    file_names = os.listdir("data/unparsed_reports")

    if ".DS_Store" in file_names:
        file_names.remove(".DS_Store")

    if not file_names:
        print("No files to parse!")
        return None

    for file in file_names:
        data = parse_reports(f"data/unparsed_reports/{file}")
        os.remove(f"data/unparsed_reports/{file}")
        print(f"Parse Successful for {file}!")
    return data


if __name__ == "__main__":
    parse_from_pdf()
