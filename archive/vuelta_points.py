import pandas as pd
from datetime import datetime

from procyclingstats import Race, Stage

import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

print(f"Running script at {datetime.now()}")

sheet_id = "1CovKWfW7MXokDt-AY6fLI7a5KDtwC781Tj2QbVD7N7o"
gid = "1366607586"
url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
df_lineup = pd.read_csv(url)
for i in range(1, 22):
    df_lineup[str(i)] = df_lineup[str(i)].str.lower()


def load_big_board():
    sheet_id = "1CovKWfW7MXokDt-AY6fLI7a5KDtwC781Tj2QbVD7N7o"
    gid = "360635960"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df_big_board = pd.read_csv(url)

    df_big_board['rider_name'] = df_big_board['rider_name'].apply(lambda x: x.lower())
    df_big_board['team_name'] = df_big_board['team_name'].str.replace(r"\s*\(.*?\)", "", regex=True).str.lower()

    return df_big_board


def load_team_board():
    sheet_id = "1CovKWfW7MXokDt-AY6fLI7a5KDtwC781Tj2QbVD7N7o"
    gid = "417478782"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)

    df['team_name'] = df['team_name'].str.replace(r"\s*\(.*?\)", "", regex=True).str.lower()

    return df


def init_dfs(users: list[str]) -> dict:
    n_stages = 21
    dfs = {}

    for user in users:
        df_user = pd.DataFrame({
            "rider": df_lineup.loc[df_lineup['user'] == user, '1']
        }).reset_index(drop=True)

        for i in range(1, n_stages + 1):
            df_user[f"stage_{i}"] = 0

        dfs[user] = df_user

    return dfs


race = Race('race/vuelta-a-espana/2025')
winners = race.stages_winners()

completed_stages = []
for i in range(21):
    if winners[i]['rider_name']:
        completed_stages.append(i+1)
print(completed_stages)


def create_results_dict(stage):
    results = stage.results()
    gc_results = stage.gc()
    points_results = stage.points()
    youth_results = stage.youth()
    kom_results = stage.kom()

    dict = {'stage_results': [r['rider_name'].lower() for r in results if r['rider_name']],
            'gc_leaders': [r['rider_name'].lower() for r in gc_results if r['rider_name']],
            'points_leaders':[r['rider_name'].lower() for r in points_results if r['rider_name']],
            'youth_leaders': [r['rider_name'].lower() for r in youth_results if r['rider_name']],
            'kom_leaders': [r['rider_name'].lower() for r in kom_results if r['rider_name']],
            'stage_bonus': [10, 0, 0, 0, 00, 0, 0, 0, 0, 0, 0, 0, 0, 20, 0, 0, 0, 10, 0, 0, 20]
            }

    return dict


def create_ttt_results_dict(stage):
    results = stage.results("team_name")
    gc_results = stage.gc()
    points_results = stage.points()
    youth_results = stage.youth()
    kom_results = stage.kom()

    results_dict = {'stage_results': list(dict.fromkeys(r["team_name"].lower() for r in results)),
                    'gc_leaders': [r['rider_name'].lower() for r in gc_results if r['rider_name']],
                    'points_leaders':[r['rider_name'].lower() for r in points_results if r['rider_name']],
                    'youth_leaders': [r['rider_name'].lower() for r in youth_results if r['rider_name']],
                    'kom_leaders': [r['rider_name'].lower() for r in kom_results if r['rider_name']],
                    'stage_bonus': [10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 20, 0, 0, 0, 10, 0, 0, 20]
                    }

    return results_dict


def gc_points(stage_number, user, df, results):
    gc_riders = set(df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'GC'), str(stage_number)])
    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for i, points in enumerate(stage_points):
        rider = results['stage_results'][i]
        if rider in gc_riders:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += points
            if i == 0:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += stage_bonus

    leader_categories = ['gc_leaders', 'points_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in gc_riders:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += 10


def sprinter_points(stage_number, user, df, results):
    sprinters = set(df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Sprinter'), str(stage_number)])
    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for i, points in enumerate(stage_points):
        rider = results['stage_results'][i]
        if rider in sprinters:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += points
            if i == 0:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += stage_bonus

    leader_categories = ['gc_leaders', 'points_leaders', 'youth_leaders', 'kom_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in sprinters:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += 10


def youth_points(stage_number, user, df, results):
    df_big_board = load_big_board()
    young_riders = set(df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Young'), str(stage_number)])
    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for rider in young_riders:
        age = int(df_big_board.loc[df_big_board['rider_name'] == rider, 'age'].iloc[0])
        age_mult = 0
        if age < 21:
            age_mult = 3
        elif age < 23:
            age_mult = 2
        elif age < 25:
            age_mult = 1.5
        else:
            age_mult = 1

        for i, points in enumerate(stage_points):
            rider = results['stage_results'][i]
            if rider in young_riders:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += (age_mult * points)
                if i == 0:
                    df.loc[df['rider'] == rider, f"stage_{stage_number}"] += (age_mult * stage_bonus)

        leader_categories = ['gc_leaders', 'points_leaders', 'youth_leaders', 'kom_leaders']
        for cat in leader_categories:
            rider = results[cat][0]
            if rider in young_riders:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += (age_mult * 10)


def climber_points(stage_number, user, df, results):
    climbers = set(df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Climber'), str(stage_number)])
    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for i, points in enumerate(stage_points):
        rider = results['stage_results'][i]
        if rider in climbers:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += points
            if i == 0:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += stage_bonus

    leader_categories = ['kom_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in climbers:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += 10


def flex_points(stage_number, user, df, results):
    flex_riders = set(df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Flex'), str(stage_number)])
    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for i, points in enumerate(stage_points):
        rider = results['stage_results'][i]
        if rider in flex_riders:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += points
            if i == 0:
                df.loc[df['rider'] == rider, f"stage_{stage_number}"] += stage_bonus

    leader_categories = ['gc_leaders', 'points_leaders', 'youth_leaders', 'kom_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in flex_riders:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += 10


def team_points(stage_number, user, df, results):
    df_big_board = load_big_board()
    df_teams = load_team_board()
    team = df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Team'), str(stage_number)].iloc[0]
    riders = set(df_big_board.loc[df_big_board['team_name'] == team, "rider_name"])
    team_mult = df_teams.loc[(df_teams['team_name'] == team), "mult"]

    stage_bonus = results['stage_bonus'][stage_number-1]
    winner = results['stage_results'][0]
    if winner in riders:
        df.loc[df['rider'] == winner, f"stage_{stage_number}"] += (team_mult * 50)
        if i == 0:
            df.loc[df['rider'] == winner, f"stage_{stage_number}"] += (team_mult * stage_bonus)

    leader_categories = ['gc_leaders', 'points_leaders', 'youth_leaders', 'kom_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in team:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += (team_mult * 10)


def itt_team_points(stage_number, user, df, results):
    df_teams = load_team_board()
    team = df_lineup.loc[(df_lineup['user'] == user) & (df_lineup['position'] == 'Team'), str(stage_number)].iloc[0]
    team_mult = df_teams.loc[(df_teams['team_name'] == team), "mult"]

    stage_points = [50, 10, 8, 6, 4]
    stage_bonus = results['stage_bonus'][stage_number-1]

    for i, points in enumerate(stage_points):
        winning_teams = results['stage_results'][i]
    if team in winning_teams:
        df.loc[df['rider'] == team, f"stage_{stage_number}"] += (team_mult * points)
        if i == 0:
            df.loc[df['rider'] == team, f"stage_{stage_number}"] += (team_mult * stage_bonus)

    leader_categories = ['gc_leaders', 'points_leaders', 'youth_leaders', 'kom_leaders']
    for cat in leader_categories:
        rider = results[cat][0]
        if rider in team:
            df.loc[df['rider'] == rider, f"stage_{stage_number}"] += (team_mult * 10)


def user_score(user, df):
    for stage_number in completed_stages:
        print(f"Processing stage {stage_number} for {user}")
        stage = Stage(f"race/vuelta-a-espana/2025/stage-{stage_number}")
        if stage.stage_type() == 'TTT':
            results = create_ttt_results_dict(stage)
            gc_points(stage_number, user, df, results)
            climber_points(stage_number, user, df, results)
            sprinter_points(stage_number, user, df, results)
            youth_points(stage_number, user, df, results)
            itt_team_points(stage_number, user, df, results)
            flex_points(stage_number, user, df, results)
        else:
            results = create_results_dict(stage)
            gc_points(stage_number, user, df, results)
            climber_points(stage_number, user, df, results)
            sprinter_points(stage_number, user, df, results)
            youth_points(stage_number, user, df, results)
            team_points(stage_number, user, df, results)
            flex_points(stage_number, user, df, results)

    df["total_points"] = df[[f"stage_{i}" for i in range(1, 22)]].sum(axis=1)


users=["Nick", "Paeyton", "Yab"]
dfs = init_dfs(users)

for user in users:
    user_score(user, dfs[user])


# ---- AUTH ----
scope = ["https://spreadsheets.google.com/feeds",
         "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file",
         "https://www.googleapis.com/auth/drive"]

creds = Credentials.from_service_account_file("/Users/connoryablonski/Dropbox/Tour_de_Frantasy/tour-de-frantasy-e070674b2fa6.json", scopes=scope)
client = gspread.authorize(creds)

# ---- OPEN SPREADSHEET ----
spreadsheet = client.open("Tour de Frantasy: Vuelta Edition")

# ---- LOOP THROUGH USERS ----
for user, df_user in dfs.items():
    try:
        # Try to open existing worksheet for user
        worksheet = spreadsheet.worksheet(user)
        worksheet.clear()  # clear old data
    except gspread.exceptions.WorksheetNotFound:
        # Create a new worksheet for this user
        worksheet = spreadsheet.add_worksheet(title=user, rows=str(len(df_user)+10), cols=str(len(df_user.columns)+10))

    # Write the DataFrame to the worksheet
    set_with_dataframe(worksheet, df_user)
