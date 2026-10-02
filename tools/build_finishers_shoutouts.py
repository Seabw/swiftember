#!/usr/bin/env python3
"""
Generate 5-week analysis and neutral, factual shoutouts for 22 selected Swiftember runners
with outstanding stats, special occasions, or notable milestones.
"""
import json
import os

SCRATCH_PATH = "/Users/bowang/.gemini/antigravity-ide/brain/5f747ba1-1978-4848-a3b6-12aec21cf04e/scratch/finishers_analysis.json"
SHOUTOUTS_PATH = os.path.join(os.path.dirname(__file__), "shoutouts.json")
ARTIFACT_PATH = "/Users/bowang/.gemini/antigravity-ide/brain/5f747ba1-1978-4848-a3b6-12aec21cf04e/swiftember_2026_finishers_shoutouts.md"

with open(SCRATCH_PATH, "r", encoding="utf-8") as f:
    all_finishers = json.load(f)

by_name = {f["name"]: f for f in all_finishers}

# 22 selected runners with neutral, factual tags and messages
selected_data = [
    # Page 4: Category Leaders, Major Surpluses, Volume Progression & 10K Milestones (11 runners)
    {
        "name": "Thomas Glave",
        "tag": "👑 Distance King • Highest Total Mileage (282.1 km)",
        "analysis": "282.1 km across 24 runs, 250 km target, 1,343 m elevation, Berlin Marathon 42.6 km.",
        "message": "Logged the highest total mileage of the challenge with 282.1 km across 24 runs, exceeding his 250 km target by 32.1 km. His month included 1,343 m of elevation gain and the Berlin Marathon (42.6 km)."
    },
    {
        "name": "Adrián Nieves",
        "tag": "💥 Target Smasher • 206.8% Goal Completion",
        "analysis": "51.7 km on 25 km target, 9 runs, 217 m elevation, returned to running 1.5 months ago.",
        "message": "Returned to running a month and a half ago, using Swiftember as the perfect motivation to keep pushing and stay consistent. Originally planning for a 25 km target, he ended up logging 51.7 km across 9 runs (206.8% completion) with 217 m of climbing."
    },
    {
        "name": "Mark Blakeman",
        "tag": "🚀 Surplus Champion (+65.0 km) • 3rd Major Star",
        "analysis": "215.0 km on 150 km target, +65.0 km surplus, 1,166 m elev, 4x 50k+ weeks, Berlin Marathon.",
        "message": "Generated the largest surplus distance in the club (+65.0 km), logging 215.0 km across 18 runs with 1,166 m of climbing. Averaged over 50 km weekly and completed the Berlin Marathon (42.7 km) to secure his 3rd World Major star."
    },
    {
        "name": "Anthony Morgan",
        "tag": "🚀 Second-Largest Surplus (+60.8 km) • 181.1% of Goal",
        "analysis": "135.8 km on 75 km target, 15 runs, 992 m elevation, consecutive 40k+ weeks.",
        "message": "Logged 135.8 km on a 75 km target (+60.8 km surplus) across 15 runs with 992 m of climbing. Established a strong early foundation with consecutive 40 km+ weeks in the first fortnight, including a 21.4 km half marathon."
    },
    {
        "name": "Joe Pinder",
        "tag": "🏃 Third-Largest Surplus (+58.2 km) • 208.2 km Logged",
        "analysis": "208.2 km on 150 km target, 17 runs, 1,324 m elevation, 3x 50k+ weeks, Berlin Marathon.",
        "message": "Finished with 208.2 km against a 150 km pledge (+58.2 km surplus) across 17 runs with 1,324 m of elevation. Maintained three separate 50 km+ training weeks before completing the Berlin Marathon (42.6 km)."
    },
    {
        "name": "Jon Williams",
        "tag": "📈 194.9% Goal Completion • Steady Volume Progression",
        "analysis": "68.2 km on 35 km target, 10 runs, 247 m elev, progressive build from 5 km to 20 km.",
        "message": "Achieved 194.9% of his monthly target, logging 68.2 km against a 35 km pledge across 10 outings. Rebuilt mileage progressively from 5.0 km in Week 1 to 20.0 km in Week 2, sustaining 16 to 22 km weekly thereafter."
    },
    {
        "name": "Andrea Bohn",
        "tag": "👟 Frequency Leader (35 km Cohort) • 21 Runs Logged",
        "analysis": "21 runs logged, 63.1 km on 35 km target (180.3%), consistent every-other-day outings.",
        "message": "Recorded 21 runs across the 5 weeks—the highest run frequency among participants with a 35 km target. Logged 63.1 km total, exceeding her pledge by 28.1 km (180.3% completion)."
    },
    {
        "name": "Richard Lakin",
        "tag": "🇩🇪 Berlin Marathon Finish • +52.1 km Surplus",
        "analysis": "152.1 km on 100 km target, 8 runs, 660 m elev, Berlin Marathon 42.6 km.",
        "message": "Logged 152.1 km on a 100 km pledge across 8 outings with 660 m of climbing (+52.1 km surplus). Completed three 30–40 km preparatory weeks, concluding with the Berlin Marathon (42.6 km) in Week 4."
    },
    {
        "name": "Bradley M 🏳️‍🌈💪🏃‍♂️",
        "tag": "⚡️ Second-Half Mileage Surge • 130.5% Goal Hit",
        "analysis": "26.1 km on 20 km target, 5 runs, back-to-back 10 km weeks in Weeks 3 & 4 (10.1 km Week 4).",
        "message": "Logged 26.1 km against a 20 km pledge across 5 runs with 126 m of elevation gain. Reached goal via back-to-back ~10 km weeks in the second half of September, including a 10.1 km run in Week 4."
    },
    {
        "name": "Laura Rafailov",
        "tag": "🎯 Sub-60 10K Milestone (58:57) • London Pride 10K",
        "analysis": "101.8 km on 100 km target, 14 runs, 666 m elevation, dedicated preparation to break 60 mins.",
        "message": "Targeted a sub-60 minute 10K milestone during Swiftember, utilizing the challenge to structure dedicated preparation. Achieved the objective at the London Pride 10K with an official finish of 58:57, concluding the month with 101.8 km logged on a 100 km pledge across 14 outings."
    },
    {
        "name": "Chris W",
        "tag": "🍁 Leafy 10K Personal Best • Bournville Return",
        "analysis": "53.6 km on 50 km target, 6 runs, 343 m elev, Leafy 10K PB in Bournville (beating last year debut).",
        "message": "Returned to Bournville for the Leafy 10K, the site of his very first race last year. Aiming for a personal best and to beat his previous year's time, he accomplished both, concluding Swiftember with 53.6 km logged on a 50 km pledge (107.2% of goal)."
    },
    {
        "name": "Jack Dean",
        "tag": "🏙 Chicago Marathon Preparation • 244.0 km Logged",
        "analysis": "244.0 km on 200 km target, 22 runs, 1,908 m elevation, 32.0 km long run.",
        "message": "Logged 244.0 km across 22 runs with 1,908 m of elevation gain as part of Chicago Marathon preparation. Maintained high weekly mileage throughout September, with a peak long run of 32.0 km."
    },

    # Page 5: Endurance Titans, Marathon Milestones & Special Spotlights (11 runners)
    {
        "name": "Christopher Bainbridge",
        "tag": "🥈 Second-Highest Distance • 264.7 km Logged",
        "analysis": "264.7 km on 250 km target, 25 runs, 1,231 m elev, consistent 60-75 km weeks, Berlin Marathon.",
        "message": "Recorded the second-highest mileage in the club with 264.7 km across 25 runs and 1,231 m of elevation. Maintained consistent weekly mileage between 60 and 75 km, including completion of the Berlin Marathon."
    },
    {
        "name": "Alice Wilkinson",
        "tag": "🏔 Endurance Titan • Longest Single Run (83.0 km)",
        "analysis": "132.6 km on 125 km target, 10 runs, 727 m elev, 83.0 km 50-mile Ultra on Sep 12.",
        "message": "Completed the longest single activity of Swiftember with an 83.0 km 50-mile ultra-marathon on September 12. Concluded the month with 132.6 km across 10 outings with 727 m of climbing (106.1% of target)."
    },
    {
        "name": "Jake Colbourn",
        "tag": "👟 Run Machine • Most Runs (27) & Elevation Record",
        "analysis": "27 runs (club high), 204.4 km, 3,074 m elevation (club record), 81.9 km 50-mile Ultra.",
        "message": "Logged the highest number of runs in the club with 27 outings, totaling 204.4 km. Set club-leading marks in elevation gain (3,074 m) and completed an 81.9 km 50-mile ultra-marathon on September 12."
    },
    {
        "name": "Adam Bown",
        "tag": "⚡️ Speed Demon • Fastest Average Pace (4:45 /km)",
        "analysis": "208.1 km on 200 km target, 21 runs, 1,727 m elev, 4:45 /km average pace, 21.2 km max.",
        "message": "Registered the fastest average pace among high-volume runners, averaging 4:45 /km across 208.1 km and 21 runs. Also accumulated 1,727 m of climbing with a longest single run of 21.2 km."
    },
    {
        "name": "Benjamin Lane",
        "tag": "⚡️ Weekly Speed Demon (Week 3) • Sub-5:00 Pacing",
        "analysis": "106.5 km on 100 km target, 11 runs, 680 m elevation, 4:58 /km pace, Week 3 Speed Demon.",
        "message": "Logged 106.5 km on a 100 km target across 11 outings with 680 m of climbing, maintaining an overall average pace of 4:58 /km. In Week 3, became the sole runner to dethrone Adam Bown for the weekly Speed Demon award, averaging 4:48 /km across 18.0 km."
    },
    {
        "name": "Alexander Brown",
        "tag": "🏅 233.2 km Total • Berlin Marathon Finish",
        "analysis": "233.2 km on 200 km target, 19 runs, 1,354 m elev, 63.6 km Week 4 peak, Berlin Marathon.",
        "message": "Completed 233.2 km across 19 runs with 1,354 m of climbing. Reached a peak volume of 63.6 km in Week 4 and completed the Berlin Marathon (42.6 km)."
    },
    {
        "name": "Bo Wang",
        "tag": "🇩🇪 Berlin Marathon Finish • 3rd Major Star",
        "analysis": "228.3 km on 200 km target, 20 runs, 5:11 /km pace, 694 m elev, Berlin Marathon 42.6 km.",
        "message": "Completed 228.3 km across 20 runs at an average pace of 5:11 /km with 694 m of elevation. Opened with an 86.1 km volume in Week 1 and completed the Berlin Marathon (42.6 km) to secure a third World Marathon Major star."
    },
    {
        "name": "Ian Allen 🏳️‍🌈",
        "tag": "⛰ Second-Highest Elevation • 1,754 m Climbing",
        "analysis": "217.6 km on 200 km target, 21 runs, 1,754 m elev (2nd highest), Berlin Marathon 42.5 km.",
        "message": "Recorded 217.6 km across 21 runs with 1,754 m of elevation gain, representing the second-highest climbing total in the club. Completed the Berlin Marathon (42.5 km) in Week 4."
    },
    {
        "name": "Joshua Savage",
        "tag": "⛰ Third-Highest Elevation • 2,759 m Climbing",
        "analysis": "201.4 km on 200 km target, 18 runs, 2,759 m elev (3rd highest), Berlin Marathon 42.6 km.",
        "message": "Accumulated 201.4 km across 18 runs and 2,759 m of elevation gain (third-highest climbing total in the club), alongside completing the Berlin Marathon (42.6 km)."
    },
    {
        "name": "Helen Williams",
        "tag": "🇫🇷🇩🇪 Dual Marathon Milestone • Paris & Berlin 2026",
        "analysis": "141.5 km on 125 km target, 11 runs, 874 m elev, completed Berlin Marathon after Paris.",
        "message": "Logged 141.5 km across 11 runs with 874 m of elevation, completing the Berlin Marathon (42.4 km). This marked her second World Marathon Major distance finish of 2026, following Paris earlier in the year."
    },
    {
        "name": "Lee Singleton",
        "tag": "🏥 Medical Comeback Milestone • 102.0 km Logged",
        "analysis": "102.0 km on 100 km target, 13 runs, 863 m elev, first 100k block since seizure recovery.",
        "message": "Completed 102.0 km across 13 runs with 863 m of elevation gain, achieving 102.0% of his 100 km pledge. This represents his first full 100 km month following medical recovery from a seizure last year."
    }
]

final_finishers_list = []
for item in selected_data:
    raw_name = item["name"]
    matched = by_name.get(raw_name)
    if not matched:
        for k in by_name:
            if raw_name.split()[0] in k:
                matched = by_name[k]
                break
    if not matched:
        print(f"Warning: Could not match {raw_name}")
        continue
    
    final_finishers_list.append({
        "rank": matched["rank"],
        "name": matched["name"],
        "target_km": matched["target"],
        "total_km": matched["total"],
        "pct_achieved": matched["pct"],
        "surplus_km": matched["surplus"],
        "total_runs": matched["runs"],
        "total_elev_m": matched["elev"],
        "avg_pace": matched["pace"],
        "longest_run_km": matched["longest"],
        "weekly_km": [w["dist"] for w in matched["weeks"]],
        "tag": item["tag"],
        "analysis": item["analysis"],
        "shoutout": item["message"]
    })

with open(SHOUTOUTS_PATH, "r", encoding="utf-8") as f:
    shoutouts_data = json.load(f)

shoutouts_data["final_finishers"] = final_finishers_list
with open(SHOUTOUTS_PATH, "w", encoding="utf-8") as f:
    json.dump(shoutouts_data, f, indent=2)

print(f"Updated {SHOUTOUTS_PATH} with {len(final_finishers_list)} selected finisher highlights.")

# Build Markdown Artifact Document
md_lines = [
    "# 🏳️‍🌈 Swiftember 2026 • Selected Member Highlights & Notable Milestones",
    "",
    "> **Featuring 22 selected runners with outstanding statistics, special occasions, and notable milestones.**",
    "> Out of 66 registered runners, **56 runners (84.8%)** achieved their goals, combining for **6,579.4 km** (114.3% of the 5,754 km club pledge), **706 runs**, and **41,917 m** of elevation gain.",
    "",
    "---",
    "",
    "## 🏆 Thematic Highlight Overview",
    "",
    "1. **👑 Distance King & Mileage Leaders**: Thomas Glave (282.1 km) and Christopher Bainbridge (264.7 km).",
    "2. **💥 Target Smasher & Surplus Leaders**: Adrián Nieves (206.8% completion), Mark Blakeman (+65.0 km surplus), Anthony Morgan (+60.8 km surplus), and Joe Pinder (+58.2 km surplus).",
    "3. **🏔 Endurance & Frequency Records**: Alice Wilkinson (83.0 km single longest run) and Jake Colbourn (27 runs, 3,074 m elevation gain).",
    "4. **⚡️ Speed & Precision**: Adam Bown (4:45 /km pace), Benjamin Lane (sole runner to dethrone Adam in Week 3, 4:48 /km), and Laura Rafailov (Pride 10K sub-60 milestone in 58:57).",
    "5. **📈 Volume Progression**: Jon Williams (194.9% build), Andrea Bohn (21 runs), and Bradley M (130.5% surge).",
    "6. **🇩🇪 Marathon Accomplishments & Debuts**: Berlin Marathon finishers (Mark Blakeman, Richard Lakin, Alexander Brown, Bo Wang, Ian Allen, Joshua Savage, Helen Williams) and Jack Dean (Chicago Marathon build).",
    "7. **🏥 Milestone Comeback**: Lee Singleton (102.0 km logged following medical recovery from a seizure).",
    "",
    "---",
    "",
    "## 📜 Individual Highlights & Analytical Breakdown (22 Selected Runners)",
    ""
]

for idx, entry in enumerate(final_finishers_list, 1):
    w_trend = " → ".join([f"W{i+1}: {k:.1f}k" for i, k in enumerate(entry["weekly_km"])])
    elev_str = f"{entry['total_elev_m']:,} m" if entry['total_elev_m'] > 0 else "--"
    md_lines.append(f"### Spotlight #{idx}: {entry['name']} (Leaderboard Rank #{entry['rank']})")
    md_lines.append(f"**Category / Milestone**: `{entry['tag']}`  ")
    md_lines.append(f"- **Challenge Target**: {entry['target_km']:.0f} km | **Total Logged**: **{entry['total_km']:.1f} km** ({entry['pct_achieved']:.1f}% • **+{entry['surplus_km']:.1f} km surplus**)")
    md_lines.append(f"- **Summary Metrics**: {entry['total_runs']} runs | Avg Pace: `{entry['avg_pace']}` | Elevation: {elev_str} | Longest Single Run: {entry['longest_run_km']:.1f} km")
    md_lines.append(f"- **5-Week Weekly Progression**: `{w_trend}`")
    md_lines.append(f"- **Analytical Commentary**: {entry['shoutout']}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

with open(ARTIFACT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"Generated Markdown artifact at {ARTIFACT_PATH}")
