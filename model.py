import pymc3 as pm
import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import pymc3 as pm
import seaborn as sns
import theano.tensor as tt

from matplotlib.ticker import StrMethodFormatter

data = pd.read_csv("all.csv", )

# select training data

df = data[data.season==2020]
df = df[["hjemme", "modstander", "score", "score_imod"]]
df.columns = ["home_team", "away_team", "home_score", "away_score"]

# the model
# goals for and against the home team are y1 and y2
# the vector of the scores are independent poison distributed
# yi | theta_j - poisson(theta_j)
# the scoring intensities, theta, are assumed to be
# log-linear:
# log theta_1 = home + att_home + def_against
# log theta_2 = att_against + def_home 

teams = df.home_team.unique()
teams = pd.DataFrame(teams, columns=["team"])
teams["i"] = teams.index

df = pd.merge(df, teams, left_on="home_team", right_on="team", how="left")
df = df.rename(columns={"i": "i_home"}).drop("team", 1)
df = pd.merge(df, teams, left_on="away_team", right_on="team", how="left")
df = df.rename(columns={"i": "i_away"}).drop("team", 1)

observed_home_goals = df.home_score.values
observed_away_goals = df.away_score.values

home_team = df.i_home.values
away_team = df.i_away.values

num_teams = len(df.i_home.drop_duplicates())
num_games = len(home_team)


# define model
with pm.Model() as model:
    # global model parameters
    home = pm.Flat("home")
    sd_att = pm.HalfStudentT("sd_att", nu=3, sigma=2.5)
    sd_def = pm.HalfStudentT("sd_def", nu=3, sigma=2.5)
    intercept = pm.Flat("intercept")

    # team-specific model parameters
    atts_star = pm.Normal("atts_star", mu=0, sigma=sd_att, shape=num_teams)
    defs_star = pm.Normal("defs_star", mu=0, sigma=sd_def, shape=num_teams)

    atts = pm.Deterministic("atts", atts_star - tt.mean(atts_star))
    defs = pm.Deterministic("defs", defs_star - tt.mean(defs_star))
    home_theta = tt.exp(intercept + home + atts[home_team] + defs[away_team])
    away_theta = tt.exp(intercept + atts[away_team] + defs[home_team])

    # likelihood of observed data
    home_goals = pm.Poisson("home_goals", mu=home_theta, observed=observed_home_goals)
    away_goals = pm.Poisson("away_goals", mu=away_theta, observed=observed_away_goals)

with model:
    trace = pm.sample(1000, tune=1000, cores=3)

pm.traceplot(trace, var_names=["intercept", "home", "sd_att", "sd_def"])



# simulate
with model:
    pp_trace = pm.sample_posterior_predictive(trace)

home_sim_df = pd.DataFrame(
    {
        f"sim_points_{i}": 3 * home_won
        for i, home_won in enumerate(pp_trace["home_goals"] > pp_trace["away_goals"])
    }
)
home_sim_df.insert(0, "team", df["home_team"])

away_sim_df = pd.DataFrame(
    {
        f"sim_points_{i}": 3 * away_won
        for i, away_won in enumerate(pp_trace["home_goals"] < pp_trace["away_goals"])
    }
)
away_sim_df.insert(0, "team", df["away_team"])

draw_sim_df = pd.DataFrame(
    {
        f"sim_points_{i}": 1 * draw
        for i, draw in enumerate(pp_trace["home_goals"] == pp_trace["away_goals"])
    }
)
draw2_sim_df = draw_sim_df.copy()
draw_sim_df.insert(0, "team", df["home_team"])
draw2_sim_df.insert(0, "team", df["away_team"])

sim_table = (
    home_sim_df.groupby("team")
    .sum()
    .add(away_sim_df.groupby("team").sum())
    .add(draw_sim_df.groupby("team").sum())
    .add(draw2_sim_df.groupby("team").sum())
    .rank(ascending=False, method="min", axis=0)
    .reset_index()
    .melt(id_vars="team", value_name="rank")
    .groupby("team")["rank"]
    .value_counts()
    .unstack(level="rank")
    .fillna(0)
)
n_samples = sim_table.sum(axis=1).values[0]  # will be the same for all teams
sim_table = sim_table.div(n_samples)

sim_table.loc[:,1.0].sort_values(ascending=False)
