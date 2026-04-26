import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import lognorm
import numpy as np


def analyze_character_performance(log_file="gap_acceptance_log.json"):
    with open(log_file, "r") as f:
        data = json.load(f)

    records = []
    gap_data = []

    for session in data:
        char = session["character"]
        summary = session["summary"]

        # Calculate survival rate for the session
        # (Assuming we track wins/losses in the log or summary)
        # For this example, we use the metrics provided in the JSON summary
        records.append({
            "Character": char,
            "Mean Gap": summary.get("mean_gap_s", 0),
            "Min Gap": summary.get("min_gap_s", 0),
            "Events": summary.get("n", 0),
            "$\mu_{ln}$": summary.get("lognormal_mu", 0),
            "$\sigma_{ln}$": summary.get("lognormal_sigma", 0)
        })

        for event in session["events"]:
            gap_data.append({
                "Character": char,
                "Gap": event["time_gap_s"]
            })

    df = pd.DataFrame(records)
    df_gaps = pd.DataFrame(gap_data)

    # Visualization
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # 1. Comparison of Risk (Accepted Gaps)
    sns.kdeplot(data=df_gaps, x="Gap", hue="Character", fill=True, ax=axes[0], palette="magma")
    axes[0].set_title("Risk Profile: Distribution of Accepted Gaps")
    axes[0].set_xlabel("Time Gap to Vehicle (seconds)")

    # 2. Performance Comparison (Average Accepted Gap)
    sns.barplot(data=df, x="Character", y="Mean Gap", ax=axes[1], palette="viridis")
    axes[1].set_title("Average Gap Acceptance by Character")
    axes[1].set_ylabel("Mean Gap (s)")

    plt.tight_layout()
    plt.savefig("character_comparison_results.png")

    # Save a summary table for the report
    comparison_summary = df.groupby("Character").mean()
    comparison_summary.to_csv("character_comparison_stats.csv")
    print("Comparison complete. Files saved: character_comparison_results.png and stats.csv")


if __name__ == "__main__":
    analyze_character_performance()