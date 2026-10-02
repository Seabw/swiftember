#!/usr/bin/env python3
"""
Swiftember 2026 - Master Weekly Report & Leaderboard Generator
Generates pixel-perfect HTML/PDF reports and formatted Slack/Markdown summaries
from Strava Club Leaderboard data.
"""

import os
import sys
import json
import argparse
import subprocess
import re
import unicodedata

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROSTER_PATH = os.path.join(BASE_DIR, "roster.json")
ALIASES_PATH = os.path.join(BASE_DIR, "aliases.json")
DATA_DIR = os.path.join(BASE_DIR, "data")

def clean_duplicated_name(name_str):
    """Removes duplicated words/halves from Strava copy-paste."""
    s = name_str.strip()
    words = s.split()
    w_len = len(words)
    if w_len >= 2 and w_len % 2 == 0:
        half = w_len // 2
        if words[:half] == words[half:]:
            return " ".join(words[:half])
    for i in range(1, len(s)):
        left = s[:i].strip()
        right = s[i:].strip()
        if left == right:
            return left
    return s

def normalize(s):
    """Normalize unicode strings for robust fuzzy/alias matching."""
    s = re.sub(r'[^\w\s]', '', s)
    return unicodedata.normalize('NFKD', s).encode('ASCII', 'ignore').decode('utf-8').strip().lower()

def parse_elev_val(e_str):
    if not e_str or str(e_str) in ['--', '-']:
        return 0
    nums = re.findall(r'\d+', str(e_str).replace(',', ''))
    return int(nums[0]) if nums else 0

def parse_pace_val(p_str):
    if not p_str or str(p_str) in ['--', '-']:
        return None
    m = re.match(r'(\d+):(\d+)', str(p_str))
    return int(m.group(1))*60 + int(m.group(2)) if m else None

def format_pace_val(secs):
    if not secs or secs >= 99999:
        return '--'
    m = int(round(secs)) // 60
    s = int(round(secs)) % 60
    return f'{m}:{s:02d} /km'

def load_roster():
    with open(ROSTER_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {r["name"]: float(r["target_km"]) for r in data["runners"]}

def load_aliases():
    if not os.path.exists(ALIASES_PATH):
        return {}
    with open(ALIASES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("aliases", {})

def load_shoutouts(week_num=1):
    path = os.path.join(BASE_DIR, "shoutouts.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(f"week_{week_num}", [])
    except Exception:
        return []

def load_final_finishers():
    path = os.path.join(BASE_DIR, "shoutouts.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("final_finishers", [])
    except Exception:
        return []

def parse_strava_table(raw_text):
    """Parses tab-separated or whitespace-separated Strava leaderboard lines."""
    entries = []
    lines = [l.strip() for l in raw_text.strip().split("\n") if l.strip()]
    
    for line in lines:
        if line.lower().startswith("rank") or line.lower().startswith("athlete"):
            continue
            
        parts = line.split("\t")
        if len(parts) >= 6:
            try:
                rank = int(parts[0].strip())
                raw_name = parts[1].strip()
                dist_str = parts[2].replace("km", "").replace(",", "").strip()
                dist = float(dist_str)
                runs = int(parts[3].strip())
                longest_str = parts[4].replace("km", "").replace(",", "").strip()
                longest = float(longest_str)
                pace = parts[5].strip()
                elev = parts[6].strip() if len(parts) > 6 else "--"
                
                clean_name = clean_duplicated_name(raw_name)
                entries.append({
                    "rank": rank,
                    "raw_name": raw_name,
                    "clean_name": clean_name,
                    "distance": dist,
                    "runs": runs,
                    "longest": longest,
                    "pace": pace,
                    "elev": elev
                })
            except Exception:
                continue
    return entries

def load_historical_stats(up_to_week):
    """
    Loads all saved weekly stats for weeks < up_to_week from data/week_{w}_stats.json.
    Returns a dict mapping runner_name -> list of weekly stat dicts:
    {
       "Runner Name": [
           {"week": 1, "distance": 86.1, "runs": 8, ...},
           ...
       ]
    }
    """
    history = {}
    if not os.path.exists(DATA_DIR):
        return history

    for w in range(1, up_to_week):
        stat_file = os.path.join(DATA_DIR, f"week_{w}_stats.json")
        if os.path.exists(stat_file):
            try:
                with open(stat_file, "r", encoding="utf-8") as f:
                    w_data = json.load(f)
                    runners = w_data.get("runners", {})
                    for r_name, r_stats in runners.items():
                        if r_name not in history:
                            history[r_name] = []
                        history[r_name].append({
                            "week": w,
                            "distance": float(r_stats.get("distance", 0.0)),
                            "runs": int(r_stats.get("runs", 0)),
                            "longest": float(r_stats.get("longest", 0.0)),
                            "elev": r_stats.get("elev", "-"),
                            "pace": r_stats.get("pace", "-"),
                        })
            except Exception as e:
                print(f"[WARN] Could not load historical stats for week {w}: {e}")
    return history

def save_week_stats(week_num, matched_runners):
    """
    Saves the current week's individual runner stats to data/week_{week_num}_stats.json.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    stat_file = os.path.join(DATA_DIR, f"week_{week_num}_stats.json")
    
    runners_dict = {}
    for r in matched_runners:
        runners_dict[r["registered_name"]] = {
            "distance": round(r["distance"], 2),
            "runs": r["runs"],
            "longest": round(r["longest"], 2),
            "pace": r["pace"],
            "elev": r["elev"],
            "monthly_target": r["monthly_target"],
            "pct_weekly": round(r["pct_weekly"], 2),
            "pct_monthly": round(r["pct_monthly"], 2),
            "status": r["status"],
            "cum_distance": round(r["cum_distance"], 2),
            "cum_runs": r["cum_runs"],
            "cum_elev": r.get("cum_elev", 0),
            "cum_pace": r.get("cum_pace_str", "-"),
            "cum_status": r["cum_status"]
        }
        
    out_obj = {
        "week": week_num,
        "total_registered": len(matched_runners),
        "active_count": len([r for r in matched_runners if r["distance"] > 0]),
        "total_distance": round(sum(r["distance"] for r in matched_runners), 2),
        "total_runs": sum(r["runs"] for r in matched_runners),
        "cum_distance": round(sum(r["cum_distance"] for r in matched_runners), 2),
        "cum_runs": sum(r["cum_runs"] for r in matched_runners),
        "runners": runners_dict
    }
    
    with open(stat_file, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Archived Week {week_num} stats to {stat_file}")

def process_swiftember_data(strava_entries, roster, aliases, week_num=1, historical_stats=None, is_final=False):
    matched_runners = []
    unmatched_registered = list(roster.keys())
    expected_week_fraction = 1.0 if is_final else min(1.0, week_num / 4.0)
    
    if historical_stats is None:
        historical_stats = {}
    
    # Process Strava athletes
    for s in strava_entries:
        c_name = s["clean_name"]
        norm_c = normalize(c_name)
        
        # 1. Check exact / normalized match in roster
        found = None
        for r in roster:
            if r.lower() == c_name.lower() or normalize(r) == norm_c:
                found = r
                break
                
        # 2. Check aliases map
        if not found:
            for alias_key, target_name in aliases.items():
                if norm_c == normalize(alias_key) and target_name in roster:
                    found = target_name
                    break
                    
        if found:
            this_elev = parse_elev_val(s.get("elev", ""))
            this_pace_s = parse_pace_val(s.get("pace", ""))

            existing = next((m for m in matched_runners if m["registered_name"] == found), None)
            if existing:
                existing["distance"] = round(existing["distance"] + s["distance"], 2)
                existing["runs"] += s["runs"]
                existing["longest"] = max(existing["longest"], s["longest"])
                existing["cum_distance"] = round(existing["cum_distance"] + s["distance"], 2)
                existing["cum_runs"] += s["runs"]
                existing["cum_elev"] += this_elev
                existing["cum_longest"] = max(existing["cum_longest"], s["longest"])
                
                if this_pace_s and s["distance"] > 0:
                    existing["_pace_sec_dist"] += this_pace_s * s["distance"]
                    existing["_pace_dist"] += s["distance"]
                    existing["cum_pace_s"] = existing["_pace_sec_dist"] / existing["_pace_dist"]
                    existing["cum_pace_str"] = format_pace_val(existing["cum_pace_s"])

                monthly_target = existing["monthly_target"]
                weekly_quota = existing["weekly_target"]
                existing["pct_monthly"] = (existing["cum_distance"] / monthly_target) * 100.0 if monthly_target > 0 else 0.0
                existing["pct_weekly"] = (existing["distance"] / weekly_quota) * 100.0 if weekly_quota > 0 else 0.0
                
                if existing["distance"] == 0:
                    existing["status"] = "⚪️ 0 km Logged"
                elif existing["pct_weekly"] >= 110.0:
                    existing["status"] = "🟢 Ahead"
                elif existing["pct_weekly"] >= 90.0:
                    existing["status"] = "🟢 On Track"
                elif existing["pct_weekly"] >= 60.0:
                    existing["status"] = "🟡 Slightly Behind"
                else:
                    existing["status"] = "🔴 Behind"
                    
                if is_final:
                    if existing["cum_distance"] == 0:
                        existing["cum_status"] = "⚪️ 0 km Logged"
                    elif existing["cum_distance"] >= monthly_target:
                        existing["cum_status"] = "🎉 Goal Achieved"
                    elif existing["pct_monthly"] >= 80.0:
                        existing["cum_status"] = f"🟢 Near Goal ({existing['pct_monthly']:.1f}%)"
                    elif existing["pct_monthly"] >= 50.0:
                        existing["cum_status"] = f"🟡 Incomplete ({existing['pct_monthly']:.1f}%)"
                    else:
                        existing["cum_status"] = f"🔴 Behind ({existing['pct_monthly']:.1f}%)"
                else:
                    cum_expected = monthly_target * expected_week_fraction
                    pct_of_expected = (existing["cum_distance"] / cum_expected) * 100.0 if cum_expected > 0 else 0.0
                    if existing["cum_distance"] == 0:
                        existing["cum_status"] = "⚪️ 0 km Logged"
                    elif existing["cum_distance"] >= monthly_target:
                        existing["cum_status"] = "🟢 Ahead"
                    elif pct_of_expected >= 110.0:
                        existing["cum_status"] = "🟢 Ahead"
                    elif pct_of_expected >= 90.0:
                        existing["cum_status"] = "🟢 On Track"
                    elif pct_of_expected >= 60.0:
                        existing["cum_status"] = "🟡 Slightly Behind"
                    else:
                        existing["cum_status"] = "🔴 Behind"
                continue

            if found in unmatched_registered:
                unmatched_registered.remove(found)
            monthly_target = roster[found]
            weekly_quota = monthly_target / 4.0
            
            # Prior historical weeks stats
            hist_list = historical_stats.get(found, [])
            prior_dist = sum(h.get("distance", 0.0) for h in hist_list)
            prior_runs = sum(h.get("runs", 0) for h in hist_list)
            prior_elev = sum(parse_elev_val(h.get("elev", "")) for h in hist_list)
            prior_longest = max([h.get("longest", 0.0) for h in hist_list], default=0.0)
            prior_pace_sec_dist = sum(parse_pace_val(h.get("pace", "")) * h.get("distance", 0.0) for h in hist_list if parse_pace_val(h.get("pace", "")) and h.get("distance", 0.0) > 0)
            prior_pace_dist = sum(h.get("distance", 0.0) for h in hist_list if parse_pace_val(h.get("pace", "")) and h.get("distance", 0.0) > 0)

            this_dist = s["distance"]
            this_runs = s["runs"]
            this_longest = s["longest"]
            
            cum_dist = round(prior_dist + this_dist, 2)
            cum_runs = prior_runs + this_runs
            cum_elev = prior_elev + this_elev
            cum_longest = max(prior_longest, this_longest)
            
            tot_pace_d = prior_pace_dist + (this_dist if this_pace_s and this_dist > 0 else 0.0)
            tot_pace_sd = prior_pace_sec_dist + (this_pace_s * this_dist if this_pace_s and this_dist > 0 else 0.0)
            cum_pace_s = (tot_pace_sd / tot_pace_d) if tot_pace_d > 0 else 99999
            cum_pace_str = format_pace_val(cum_pace_s) if tot_pace_d > 0 else "--"

            pct_monthly = (cum_dist / monthly_target) * 100.0 if monthly_target > 0 else 0.0
            pct_weekly = (this_dist / weekly_quota) * 100.0 if weekly_quota > 0 else 0.0
            
            # Pacing status for this week (Weekly Leaderboard)
            if this_dist == 0:
                week_status = "⚪️ 0 km Logged"
            elif pct_weekly >= 110.0:
                week_status = "🟢 Ahead"
            elif pct_weekly >= 90.0:
                week_status = "🟢 On Track"
            elif pct_weekly >= 60.0:
                week_status = "🟡 Slightly Behind"
            else:
                week_status = "🔴 Behind"
                
            if is_final:
                if cum_dist == 0:
                    cum_status = "⚪️ 0 km Logged"
                elif cum_dist >= monthly_target:
                    cum_status = "🎉 Goal Achieved"
                elif pct_monthly >= 80.0:
                    cum_status = f"🟢 Near Goal ({pct_monthly:.1f}%)"
                elif pct_monthly >= 50.0:
                    cum_status = f"🟡 Incomplete ({pct_monthly:.1f}%)"
                else:
                    cum_status = f"🔴 Behind ({pct_monthly:.1f}%)"
            else:
                cum_expected = monthly_target * expected_week_fraction
                pct_of_expected = (cum_dist / cum_expected) * 100.0 if cum_expected > 0 else 0.0
                if cum_dist == 0:
                    cum_status = "⚪️ 0 km Logged"
                elif cum_dist >= monthly_target:
                    cum_status = "🟢 Ahead"
                elif pct_of_expected >= 110.0:
                    cum_status = "🟢 Ahead"
                elif pct_of_expected >= 90.0:
                    cum_status = "🟢 On Track"
                elif pct_of_expected >= 60.0:
                    cum_status = "🟡 Slightly Behind"
                else:
                    cum_status = "🔴 Behind"
                
            matched_runners.append({
                "registered_name": found,
                "strava_name": c_name,
                "monthly_target": monthly_target,
                "weekly_target": weekly_quota,
                "distance": this_dist,
                "runs": this_runs,
                "longest": this_longest,
                "pace": s["pace"],
                "elev": s["elev"],
                "pct_monthly": pct_monthly,
                "pct_weekly": pct_weekly,
                "status": week_status,
                "strava_rank": s["rank"],
                "prior_distance": prior_dist,
                "prior_runs": prior_runs,
                "cum_distance": cum_dist,
                "cum_runs": cum_runs,
                "cum_elev": cum_elev,
                "cum_longest": cum_longest,
                "cum_pace_s": cum_pace_s,
                "cum_pace_str": cum_pace_str,
                "_pace_sec_dist": tot_pace_sd,
                "_pace_dist": tot_pace_d,
                "cum_status": cum_status
            })
            
    # Process registered runners with 0 km recorded this week
    for r in unmatched_registered:
        monthly_target = roster[r]
        weekly_quota = monthly_target / 4.0
        
        hist_list = historical_stats.get(r, [])
        prior_dist = sum(h.get("distance", 0.0) for h in hist_list)
        prior_runs = sum(h.get("runs", 0) for h in hist_list)
        prior_elev = sum(parse_elev_val(h.get("elev", "")) for h in hist_list)
        prior_longest = max([h.get("longest", 0.0) for h in hist_list], default=0.0)
        prior_pace_sec_dist = sum(parse_pace_val(h.get("pace", "")) * h.get("distance", 0.0) for h in hist_list if parse_pace_val(h.get("pace", "")) and h.get("distance", 0.0) > 0)
        prior_pace_dist = sum(h.get("distance", 0.0) for h in hist_list if parse_pace_val(h.get("pace", "")) and h.get("distance", 0.0) > 0)

        cum_dist = prior_dist
        cum_runs = prior_runs
        cum_elev = prior_elev
        cum_longest = prior_longest
        cum_pace_s = (prior_pace_sec_dist / prior_pace_dist) if prior_pace_dist > 0 else 99999
        cum_pace_str = format_pace_val(cum_pace_s) if prior_pace_dist > 0 else "--"

        pct_monthly = (cum_dist / monthly_target) * 100.0 if monthly_target > 0 else 0.0
        pct_weekly = 0.0
        week_status = "⚪️ 0 km Logged"
        
        if is_final:
            if cum_dist == 0:
                cum_status = "⚪️ 0 km Logged"
            elif cum_dist >= monthly_target:
                cum_status = "🎉 Goal Achieved"
            elif pct_monthly >= 80.0:
                cum_status = f"🟢 Near Goal ({pct_monthly:.1f}%)"
            elif pct_monthly >= 50.0:
                cum_status = f"🟡 Incomplete ({pct_monthly:.1f}%)"
            else:
                cum_status = f"🔴 Behind ({pct_monthly:.1f}%)"
        else:
            cum_expected = monthly_target * expected_week_fraction
            pct_of_expected = (cum_dist / cum_expected) * 100.0 if cum_expected > 0 else 0.0
            if cum_dist == 0:
                cum_status = "⚪️ 0 km Logged"
            elif pct_of_expected >= 110.0:
                cum_status = "🟢 Ahead"
            elif pct_of_expected >= 90.0:
                cum_status = "🟢 On Track"
            elif pct_of_expected >= 60.0:
                cum_status = "🟡 Slightly Behind"
            else:
                cum_status = "🔴 Behind"
            
        matched_runners.append({
            "registered_name": r,
            "strava_name": "-",
            "monthly_target": monthly_target,
            "weekly_target": weekly_quota,
            "distance": 0.0,
            "runs": 0,
            "longest": 0.0,
            "pace": "-",
            "elev": "-",
            "pct_monthly": pct_monthly,
            "pct_weekly": pct_weekly,
            "status": week_status,
            "strava_rank": "-",
            "prior_distance": prior_dist,
            "prior_runs": prior_runs,
            "cum_distance": cum_dist,
            "cum_runs": cum_runs,
            "cum_elev": cum_elev,
            "cum_longest": cum_longest,
            "cum_pace_s": cum_pace_s,
            "cum_pace_str": cum_pace_str,
            "_pace_sec_dist": prior_pace_sec_dist,
            "_pace_dist": prior_pace_dist,
            "cum_status": cum_status
        })
        
    return matched_runners

def generate_html_report(matched_runners, week_num=1, badge_subtitle="Official Swiftember Report", font_size="large", is_final=False):
    # Target calculations
    weekly_active = [m for m in matched_runners if m["distance"] > 0]
    mtd_active = [m for m in matched_runners if m["cum_distance"] > 0]
    goal_achievers = [m for m in matched_runners if m["cum_distance"] >= m["monthly_target"]]

    total_pledge = sum(m["monthly_target"] for m in matched_runners)
    total_cum_logged = sum(m["cum_distance"] for m in matched_runners)
    total_week_logged = sum(m["distance"] for m in matched_runners)
    expected_cum_target = total_pledge * (1.0 if is_final else min(1.0, week_num / 4.0))
    pct_total_month = (total_cum_logged / total_pledge) * 100.0 if total_pledge > 0 else 0.0
    pct_pace_rate = (total_cum_logged / expected_cum_target) * 100.0 if expected_cum_target > 0 else 0.0
    total_cum_runs = sum(m["cum_runs"] for m in matched_runners)
    total_cum_elev = sum(m.get("cum_elev", 0) for m in matched_runners)
    total_week_runs = sum(m["runs"] for m in matched_runners)
    pct_achievers = (len(goal_achievers) / len(matched_runners) * 100.0) if matched_runners else 0.0
    
    # Barriers between short, medium, and long distance runners decided by average target distance submitted by members
    avg_target = (total_pledge / len(matched_runners)) if matched_runners else 100.0
    short_barrier = round((avg_target * 0.5) / 25.0) * 25.0 if avg_target >= 40 else round(avg_target * 0.5)
    long_barrier = round(avg_target / 25.0) * 25.0 if avg_target >= 40 else round(avg_target)

    def parse_elev(e_str):
        nums = re.findall(r'\d+', str(e_str).replace(",", ""))
        return int(nums[0]) if nums else 0

    def parse_pace(p_str):
        m = re.match(r'(\d+):(\d+)', str(p_str))
        return int(m.group(1))*60 + int(m.group(2)) if m else 99999

    if is_final:
        # Hall of Fame: Distance King, Endurance Titan, Target Smasher, Run Machine, Speed Demon
        dist_king = max(mtd_active, key=lambda x: x["cum_distance"]) if mtd_active else None
        endurance_titan = max(mtd_active, key=lambda x: (x.get("cum_longest", 0.0), x["cum_distance"])) if mtd_active else None
        target_smasher = max(mtd_active, key=lambda x: (x["pct_monthly"], x["cum_distance"])) if mtd_active else None
        
        run_machine = max(mtd_active, key=lambda x: (x.get("cum_runs", 0), x["cum_distance"])) if mtd_active else None
        
        for r in mtd_active:
            r["surplus_km"] = round(r["cum_distance"] - r["monthly_target"], 2)
        surplus_candidates = [m for m in mtd_active if m.get("surplus_km", 0) > 0]
        surplus_leader = max(surplus_candidates, key=lambda x: (x["surplus_km"], x["cum_distance"])) if surplus_candidates else None
    else:
        # Weekly heroes
        short_active = [m for m in weekly_active if m["monthly_target"] <= short_barrier]
        rising_swift = max(short_active, key=lambda x: (x["pct_weekly"], x["distance"])) if short_active else None

        med_active = [m for m in weekly_active if short_barrier < m["monthly_target"] <= long_barrier]
        pace_setter = max(med_active, key=lambda x: (x["pct_weekly"], x["distance"])) if med_active else None

        long_active = [m for m in weekly_active if m["monthly_target"] > long_barrier]
        road_warrior = max(long_active, key=lambda x: (x["pct_weekly"], x["distance"])) if long_active else None
        
        elev_runner = max(weekly_active, key=lambda x: parse_elev(x["elev"])) if weekly_active else None
        speed_runner = min([m for m in weekly_active if parse_pace(m["pace"]) < 99999], key=lambda x: parse_pace(x["pace"])) if weekly_active else None

    # Sortings
    by_weekly_pct = sorted(weekly_active, key=lambda x: (x["pct_weekly"], x["distance"]), reverse=True)
    all_sorted = sorted(matched_runners, key=lambda x: (x["cum_distance"] > 0, x["pct_monthly"], x["cum_distance"]), reverse=True)

    # HTML Rows - Weekly Leaderboard (Focused on This Week's Performance)
    target_rows = ""
    for i, r in enumerate(by_weekly_pct, 1):
        pct_w = r['pct_weekly']
        weekly_quota = r['monthly_target'] / 4.0
        bar_color = "green" if pct_w >= 90 else ("yellow" if pct_w >= 60 else "red")
        badge_cls = "badge-ahead" if "Ahead" in r['status'] else ("badge-track" if "On Track" in r['status'] else ("badge-slight" if "Slightly" in r['status'] else "badge-behind"))
        bar_width = min(100, int(pct_w))
        target_rows += f"""
            <tr>
                <td class="text-center" style="font-weight: 700;">{i}</td>
                <td style="font-weight: 600;">{r['registered_name']}</td>
                <td class="text-right" style="font-weight: 700;">{r['distance']:.1f} km</td>
                <td class="text-right">{weekly_quota:.1f} km</td>
                <td class="text-center">
                    <div class="progress-cell">
                        <span class="progress-val">{pct_w:.1f}%</span>
                        <div class="progress-bar-container"><div class="progress-bar {bar_color}" style="width: {bar_width}%;"></div></div>
                    </div>
                </td>
                <td class="text-right">{r['elev']}</td>
                <td class="text-center"><span class="status-badge {badge_cls}">{r['status']}</span></td>
            </tr>
        """

    # HTML Rows - Top 5 Fastest Pacers of the Week
    valid_pacers = [m for m in weekly_active if parse_pace(m.get("pace", "")) < 99999 and m.get("distance", 0) > 0]
    top_5_pacers = sorted(valid_pacers, key=lambda x: parse_pace(x["pace"]))[:5]
    fastest_rows = ""
    medals = ["🥇 1", "🥈 2", "🥉 3", "4", "5"]
    for idx, r in enumerate(top_5_pacers):
        rank_str = medals[idx] if idx < len(medals) else str(idx + 1)
        rank_cls = "rank-1" if idx == 0 else ""
        pct_m = r['pct_monthly']
        if r['cum_distance'] >= r['monthly_target']:
            badge_html = f'<span class="status-badge badge-ahead">🎉 Done ({pct_m:.1f}%)</span>'
        else:
            cum_expected = r['monthly_target'] * min(1.0, week_num / 4.0)
            badge_cls = "badge-track" if r['cum_distance'] >= (cum_expected * 0.9) else "badge-slight"
            badge_html = f'<span class="status-badge {badge_cls}">{r["cum_distance"]:.1f} / {r["monthly_target"]:.0f} km ({pct_m:.1f}%)</span>'

        fastest_rows += f"""
            <tr>
                <td class="text-center" style="font-weight: 700;">{rank_str}</td>
                <td style="font-weight: 600;">{r['registered_name']}</td>
                <td class="text-center"><span class="pace-badge {rank_cls}">⚡️ {r['pace']}</span></td>
                <td class="text-right" style="font-weight: 700;">{r['distance']:.1f} km</td>
                <td class="text-center">{r['runs']}</td>
                <td class="text-right">{r['longest']:.1f} km</td>
                <td class="text-right">{r['elev']}</td>
                <td class="text-center">{badge_html}</td>
            </tr>
        """

    fastest_pacers_html = ""
    if fastest_rows and not is_final:
        fastest_title = "⚡️ TOP 5 FASTEST PACERS OF THE WEEK"
        fastest_pacers_html = f"""
    <div class="fastest-section" style="page-break-inside: avoid; break-inside: avoid; margin-top: 14px; margin-bottom: 8px;">
        <div class="section-title" style="margin-top: 0;">{fastest_title}</div>
        <table class="fastest-table">
            <thead>
                <tr>
                    <th class="text-center" style="width: 44px;">Rank</th>
                    <th>Runner Name</th>
                    <th class="text-center">Average Pace</th>
                    <th class="text-right">Week Logged</th>
                    <th class="text-center">Runs</th>
                    <th class="text-right">Longest Run</th>
                    <th class="text-right">Elevation</th>
                    <th class="text-center">Challenge Status</th>
                </tr>
            </thead>
            <tbody>
                {fastest_rows}
            </tbody>
        </table>
    </div>
        """

    # HTML Rows - Main Leaderboard Table
    roster_rows = ""
    for i, r in enumerate(all_sorted, 1):
        pct_m = r['pct_monthly']
        elev_str = f"{r.get('cum_elev', 0):,} m" if r.get('cum_elev', 0) > 0 else "--"

        if is_final:
            if r['cum_distance'] == 0:
                badge_cls = "badge-zero"
                status_text = "⚪️ 0 km Logged"
                bar_html = '<div class="progress-cell"><span class="progress-val" style="color: #94a3b8;">0.0%</span><div class="progress-bar-container"><div class="progress-bar" style="width: 0%;"></div></div></div>'
            else:
                if r['cum_distance'] >= r['monthly_target']:
                    badge_cls = "badge-ahead"
                    status_text = "🎉 Goal Achieved"
                    bar_color = "green"
                elif pct_m >= 80.0:
                    badge_cls = "badge-track"
                    status_text = f"🟢 Near Goal ({pct_m:.1f}%)"
                    bar_color = "green"
                elif pct_m >= 50.0:
                    badge_cls = "badge-slight"
                    status_text = f"🟡 Incomplete ({pct_m:.1f}%)"
                    bar_color = "yellow"
                else:
                    badge_cls = "badge-behind"
                    status_text = f"🔴 Behind ({pct_m:.1f}%)"
                    bar_color = "red"
                bar_width = min(100, int(pct_m))
                bar_html = f'<div class="progress-cell"><span class="progress-val">{pct_m:.1f}%</span><div class="progress-bar-container"><div class="progress-bar {bar_color}" style="width: {bar_width}%;"></div></div></div>'

            roster_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700;">{i}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-right">{r['monthly_target']:.0f} km</td>
                    <td class="text-right" style="font-weight: 700; color: {'#0f172a' if r['cum_distance'] > 0 else '#94a3b8'};">{r['cum_distance']:.1f} km</td>
                    <td class="text-center">{bar_html}</td>
                    <td class="text-center"><span class="status-badge {badge_cls}">{status_text}</span></td>
                </tr>
            """
        else:
            rem_km = max(0.0, r['monthly_target'] - r['cum_distance'])
            rem_text = f"{rem_km:.1f} km" if r['cum_distance'] < r['monthly_target'] else "🎉 Done!"
            if r['cum_distance'] == 0:
                badge_cls = "badge-zero"
                status_text = "⚪️ 0 km Logged"
                bar_html = '<div class="progress-cell"><span class="progress-val" style="color: #94a3b8;">0.0%</span><div class="progress-bar-container"><div class="progress-bar" style="width: 0%;"></div></div></div>'
                rem_text = f"{r['monthly_target']:.0f} km"
            else:
                badge_cls = "badge-ahead" if "Ahead" in r['cum_status'] else ("badge-track" if "On Track" in r['cum_status'] else ("badge-slight" if "Slightly" in r['cum_status'] else "badge-behind"))
                status_text = r['cum_status']
                cum_expected = r['monthly_target'] * min(1.0, week_num / 4.0)
                pct_of_expected = (r['cum_distance'] / cum_expected) * 100.0 if cum_expected > 0 else 0.0
                bar_color = "green" if pct_of_expected >= 90 else ("yellow" if pct_of_expected >= 60 else "red")
                bar_width = min(100, int(pct_m))
                bar_html = f'<div class="progress-cell"><span class="progress-val">{pct_m:.1f}%</span><div class="progress-bar-container"><div class="progress-bar {bar_color}" style="width: {bar_width}%;"></div></div></div>'

            roster_rows += f"""
                <tr>
                    <td class="text-center">{i}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-right">{r['monthly_target']:.0f} km</td>
                    <td class="text-right" style="font-weight: 700; color: {'#0f172a' if r['cum_distance'] > 0 else '#94a3b8'};">{r['cum_distance']:.1f} km</td>
                    <td class="text-right" style="color: {'#475569' if r['cum_distance'] > 0 else '#94a3b8'}; font-weight: 500;">{rem_text}</td>
                    <td class="text-center">{bar_html}</td>
                    <td class="text-center"><span class="status-badge {badge_cls}">{status_text}</span></td>
                </tr>
            """

    logo_path = os.path.join(BASE_DIR, "assets", "swifts_logo.jpg")
    logo_html = ""
    if os.path.exists(logo_path):
        import base64
        with open(logo_path, "rb") as img_f:
            b64 = base64.b64encode(img_f.read()).decode("utf-8")
            logo_html = f'<img src="data:image/jpeg;base64,{b64}" alt="Swifts Logo" style="height: 48px; max-width: 120px; object-fit: contain; border-radius: 6px; background: #ffffff; padding: 2px 6px; box-shadow: 0 2px 5px rgba(0,0,0,0.15); margin-right: 4px;">'

    # Build Shout-outs HTML (only for weekly reports)
    shoutouts_html = ""
    if not is_final:
        shoutouts = load_shoutouts(week_num)
        if shoutouts:
            if isinstance(shoutouts, dict) and shoutouts.get("type") == "berlin_marathon_special":
                title = shoutouts.get("title", "🇩🇪 SPECIAL EVENT SPOTLIGHT • BMW BERLIN MARATHON 2026")
                headline = shoutouts.get("headline", "ALL THE BEST TO OUR 13 BERLIN MARATHON SWIFTS! 🏃‍♂️💨🇩🇪")
                badge_major = shoutouts.get("badge_major", "🇩🇪 WORLD MARATHON MAJOR")
                badge_event = shoutouts.get("badge_event", "BMW BERLIN MARATHON 2026 • SUN 27 SEP")
                intro = shoutouts.get("intro", "")
                footer_text = shoutouts.get("footer", "")
                runners = shoutouts.get("runners", [])
                
                cards_html = ""
                for i, s in enumerate(runners):
                    tag_html = f'<span class="berlin-card-tag">{s["tag"]}</span>' if s.get("tag") else ""
                    cards_html += f"""
                        <div class="berlin-card">
                            <div class="berlin-card-header">
                                <span class="berlin-card-name">🏃 {s['name']}</span>
                                {tag_html}
                            </div>
                            <div class="berlin-card-msg">{s['message']}</div>
                        </div>
                    """
                
                additional = shoutouts.get("additional_shoutouts", [])
                additional_html = ""
                if additional:
                    add_cards_html = ""
                    for s in additional:
                        tag_html = f'<span class="shoutout-tag">{s["tag"]}</span>' if s.get("tag") else ""
                        runners_html = ""
                        if s.get("runners_list"):
                            pills = "".join([f'<span class="pride-runner-pill">🏃 {r}</span>' for r in s["runners_list"]])
                            runners_html = f'<div class="pride-runners-grid">{pills}</div>'
                        add_cards_html += f"""
                            <div class="shoutout-card">
                                <div class="shoutout-header">
                                    <span class="shoutout-name">{s['name']}</span>
                                    {tag_html}
                                </div>
                                <div class="shoutout-msg">{s['message']}</div>
                                {runners_html}
                            </div>
                        """
                    additional_html = f"""
                        <div class="shoutouts-container">
                            <div class="section-title" style="margin-top: 6px; margin-bottom: 12px; font-size: 15px; padding-bottom: 6px;">📣 MEMBER SPOTLIGHT & EVENT RECOGNITIONS</div>
                            <div class="shoutouts-grid">
                                {add_cards_html}
                            </div>
                            <div class="shoutouts-footer">Member highlights and event recognitions will continue in subsequent weekly reports.</div>
                        </div>
                    """

                shoutouts_html = f"""
                    <div class="berlin-container">
                        <div class="berlin-hero">
                            <div class="berlin-flag-stripe"></div>
                            <div class="berlin-hero-content">
                                <div class="berlin-top-row">
                                    <span class="berlin-pill">{badge_major}</span>
                                    <span class="berlin-date-pill">{badge_event}</span>
                                </div>
                                <h2 class="berlin-headline">{headline}</h2>
                                <p class="berlin-intro">{intro}</p>
                            </div>
                        </div>
                        <div class="berlin-grid">
                            {cards_html}
                        </div>
                        <div class="berlin-footer">
                            {footer_text}
                        </div>
                    </div>
                    {f'<div class="page-break"></div>{additional_html}' if additional_html else ''}
                """
            elif isinstance(shoutouts, list):
                cards_html = ""
                for s in shoutouts:
                    tag_html = f'<span class="shoutout-tag">{s["tag"]}</span>' if s.get("tag") else ""
                    cards_html += f"""
                        <div class="shoutout-card">
                            <div class="shoutout-header">
                                <span class="shoutout-name">{s['name']}</span>
                                {tag_html}
                            </div>
                            <div class="shoutout-msg">{s['message']}</div>
                        </div>
                    """
                shoutouts_html = f"""
                    <div class="shoutouts-container">
                        <div class="section-title" style="margin-top: 6px; margin-bottom: 12px; font-size: 15px; padding-bottom: 6px;">📣 MEMBER SPOTLIGHT & EVENT RECOGNITIONS</div>
                        <div class="shoutouts-grid">
                            {cards_html}
                        </div>
                        <div class="shoutouts-footer">Member highlights and event recognitions will continue in subsequent weekly reports.</div>
                    </div>
                """

    # Font sizing presets (large vs compact)
    if font_size == "large":
        body_font = "14px"
        table_font = "13px"
        th_pad = "4.5px 8px"
        th_font = "10px"
        td_pad = "4.0px 8px"
        badge_font = "9.5px"
        badge_pad = "3px 8px"
        prog_val_font = "10.5px"
        prog_bar_w = "55px"
        prog_bar_h = "5.5px"
        super_award_font = "12px"
        super_sub_font = "9px"
        super_winner_font = "13.5px"
        super_stat_font = "10px"
        metric_val_font = "24px"
        metric_lbl_font = "11px"
        metric_sub_font = "10px"
        shout_name_font = "24px"
        shout_tag_font = "14px"
        shout_msg_font = "19px"
        shout_footer_font = "14px"
        berlin_headline_font = "22px"
        berlin_intro_font = "13px"
        berlin_name_font = "15.5px"
        berlin_tag_font = "11.8px"
        berlin_msg_font = "13.2px"
        berlin_footer_font = "13px"
    else: # compact preset
        body_font = "10px"
        table_font = "9px"
        th_pad = "5px 6px"
        th_font = "8px"
        td_pad = "4.5px 6px"
        badge_font = "8px"
        badge_pad = "2px 6px"
        prog_val_font = "8.5px"
        prog_bar_w = "48px"
        prog_bar_h = "4.5px"
        super_award_font = "8.5px"
        super_sub_font = "7.5px"
        super_winner_font = "10.5px"
        super_stat_font = "9px"
        metric_val_font = "18px"
        metric_lbl_font = "9.5px"
        metric_sub_font = "8.5px"
        shout_name_font = "14px"
        shout_tag_font = "11px"
        shout_msg_font = "14px"
        shout_footer_font = "10px"
        berlin_headline_font = "14px"
        berlin_intro_font = "9.5px"
        berlin_name_font = "11px"
        berlin_tag_font = "8.5px"
        berlin_msg_font = "9px"
        berlin_footer_font = "9px"

    shout_card_pad = "10px 16px"
    shout_grid_gap = "10px"
    berlin_hero_pad = "11px 16px"
    berlin_hero_mb = "9px"
    berlin_grid_gap = "7px"
    berlin_card_pad = "7.5px 11px"
    berlin_footer_pad = "7px 14px"
    pride_pill_font = "16px"
    pride_pill_pad = "4.5px 12px"

    if is_final:
        card1_val = f"{total_pledge:,.0f} km"
        card1_lbl = "Total Month Pledge"
        card1_sub = f"{len(matched_runners)} Registered Runners"

        card2_val = f"{total_cum_logged:,.1f} km"
        card2_lbl = "Total Distance Logged"
        card2_sub = f"{pct_total_month:.1f}% of Challenge Goal"

        card3_val = f"{pct_total_month:.1f}%"
        card3_lbl = "Challenge Target Progress"
        card3_sub = f"{total_cum_logged:,.1f} / {total_pledge:,.1f} km Goal"

        card4_val = f"{len(goal_achievers)} / {len(matched_runners)}"
        card4_lbl = f"Goal Achievers ({pct_achievers:.1f}%)"
        card4_sub = f"{len(goal_achievers)} Smashed Goal • {total_cum_runs} Total Runs"
    else:
        card1_val = f"{total_pledge:,.0f} km"
        card1_lbl = "Total Month Pledge"
        card1_sub = f"{len(matched_runners)} Registered Runners"

        card2_val = f"{total_cum_logged:,.1f} km"
        card2_lbl = "Distance Logged (MTD)" if week_num > 1 else "Distance Logged"
        period_name = f"W{week_num}"
        card2_sub = f"{pct_total_month:.1f}% of Monthly Goal ({total_week_logged:,.1f} km in {period_name})" if week_num > 1 else f"{pct_total_month:.1f}% of Monthly Goal"

        card3_val = f"{pct_pace_rate:.1f}%"
        card3_lbl = f"Week {week_num} Pace Progress"
        card3_sub = f"{total_cum_logged:,.1f} / {expected_cum_target:,.1f} km Target"

        card4_val = f"{len(mtd_active)} / {len(matched_runners)}"
        card4_lbl = "Active Runners (MTD)" if week_num > 1 else "Active Runners"
        card4_sub = f"{total_cum_runs} Total Runs ({len(weekly_active)} active in {period_name})" if week_num > 1 else f"{total_cum_runs} Total Runs"

    # Middle section (shoutouts)
    if shoutouts_html and not is_final:
        middle_section = f"""
        <div class="page-break"></div>
        {shoutouts_html}
        <div class="page-break"></div>
        """
    elif not is_final:
        middle_section = """
        <div class="page-break"></div>
        """
    else:
        middle_section = ""

    doc_title = "Swiftember 2026 - Final Challenge Report" if is_final else f"Swiftember 2026 - Week {week_num} Progress Report"
    header_subtitle = "Final Month-End Wrap-Up & Full Challenge Results" if is_final else f"Week {week_num} Progress & Leaderboard Report"
    hero_section_title = "⚡️ SWIFTEMBER 2026 • HALL OF FAME" if is_final else "⚡️ WEEKLY SWIFTEMBER HEROES"

    if is_final:
        dist_king_stat = f"{dist_king['cum_distance']:.1f} km ({dist_king['cum_runs']} runs)" if dist_king else "-"
        endurance_stat = f"{endurance_titan['cum_longest']:.1f} km (50-Mile Ultra)" if (endurance_titan and endurance_titan['cum_longest'] >= 80) else (f"{endurance_titan['cum_longest']:.1f} km Single Run" if endurance_titan else "-")
        target_smasher_stat = f"{target_smasher['pct_monthly']:.1f}% of Goal ({target_smasher['cum_distance']:.1f} / {target_smasher['monthly_target']:.0f} km)" if target_smasher else "-"
        run_machine_stat = f"{run_machine['cum_runs']} Runs Logged ({run_machine['cum_distance']:.1f} km)" if run_machine else "-"
        surplus_stat = f"+{surplus_leader['surplus_km']:.1f} km Surplus ({surplus_leader['cum_distance']:.1f} km Logged)" if surplus_leader else "-"

        hero_cards_html = f"""
        <div class="super-card">
            <div class="super-icon">👑</div>
            <div class="super-award">Distance King</div>
            <div class="super-sub">Most Distance Logged</div>
            <div class="super-winner">{dist_king['registered_name'] if dist_king else '-'}</div>
            <div class="super-stat">{dist_king_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🦅</div>
            <div class="super-award">Endurance Titan</div>
            <div class="super-sub">Single Longest Run</div>
            <div class="super-winner">{endurance_titan['registered_name'] if endurance_titan else '-'}</div>
            <div class="super-stat">{endurance_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">💥</div>
            <div class="super-award">Target Smasher</div>
            <div class="super-sub">Highest Goal %</div>
            <div class="super-winner">{target_smasher['registered_name'] if target_smasher else '-'}</div>
            <div class="super-stat">{target_smasher_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">👟</div>
            <div class="super-award">Run Machine</div>
            <div class="super-sub">Most Runs Logged</div>
            <div class="super-winner">{run_machine['registered_name'] if run_machine else '-'}</div>
            <div class="super-stat">{run_machine_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🚀</div>
            <div class="super-award">Surplus Distance</div>
            <div class="super-sub">Most Distance Over Target</div>
            <div class="super-winner">{surplus_leader['registered_name'] if surplus_leader else '-'}</div>
            <div class="super-stat">{surplus_stat}</div>
        </div>
        """
    else:
        rising_swift_stat = f"{rising_swift['pct_weekly']:.1f}% Weekly Goal ({rising_swift['distance']:.1f} km)" if rising_swift else "-"
        goal_setter_stat = f"{pace_setter['pct_weekly']:.1f}% Weekly Goal ({pace_setter['distance']:.1f} km)" if pace_setter else "-"
        road_warrior_stat = f"{road_warrior['pct_weekly']:.1f}% Weekly Goal ({road_warrior['distance']:.1f} km)" if road_warrior else "-"
        elev_stat = f"{elev_runner['elev']} Elevation" if elev_runner else "-"
        speed_stat = f"{speed_runner['pace']} ({speed_runner['distance']:.1f} km)" if speed_runner else "-"
        super_sub_elev = "Most Elevation"
        super_sub_speed = "Fastest Avg Pace"

        hero_cards_html = f"""
        <div class="super-card">
            <div class="super-icon">🐣</div>
            <div class="super-award">Rising Swift</div>
            <div class="super-sub">Short Target (≤ {short_barrier:.0f} km)</div>
            <div class="super-winner">{rising_swift['registered_name'] if rising_swift else '-'}</div>
            <div class="super-stat">{rising_swift_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🌟</div>
            <div class="super-award">Goal Setter</div>
            <div class="super-sub">Medium Target ({short_barrier+1:.0f}–{long_barrier:.0f} km)</div>
            <div class="super-winner">{pace_setter['registered_name'] if pace_setter else '-'}</div>
            <div class="super-stat">{goal_setter_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🔥</div>
            <div class="super-award">Road Warrior</div>
            <div class="super-sub">Long Target (> {long_barrier:.0f} km)</div>
            <div class="super-winner">{road_warrior['registered_name'] if road_warrior else '-'}</div>
            <div class="super-stat">{road_warrior_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🏔</div>
            <div class="super-award">Mountain Goat</div>
            <div class="super-sub">{super_sub_elev}</div>
            <div class="super-winner">{elev_runner['registered_name'] if elev_runner else '-'}</div>
            <div class="super-stat">{elev_stat}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">⚡️</div>
            <div class="super-award">Speed Demon</div>
            <div class="super-sub">{super_sub_speed}</div>
            <div class="super-winner">{speed_runner['registered_name'] if speed_runner else '-'}</div>
            <div class="super-stat">{speed_stat}</div>
        </div>
        """

    footer_text = f"🏳️‍🌈 Birmingham Swifts Running Club • Swiftember 2026 Challenge Final Results • Smashed: {total_cum_logged:,.1f} km ({pct_total_month:.1f}% of {total_pledge:,.0f} km goal) • {total_cum_runs} Total Runs • {len(goal_achievers)} Goal Achievers! 🏃‍♂️💨" if is_final else "Swiftember 2026 Challenge Report • Birmingham Swifts Running Club"

    category_leaderboards_html = ""
    if is_final:
        medals = ["🥇", "🥈", "🥉", "4", "5", "6", "7", "8", "9", "10"]

        # 1. Total Distance (Top 10)
        top_dist = sorted(mtd_active, key=lambda x: x["cum_distance"], reverse=True)[:10]
        dist_rows = ""
        for idx, r in enumerate(top_dist):
            rank_str = medals[idx]
            dist_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700; font-size: 11px;">{rank_str}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-right" style="font-weight: 700; color: #1e1b4b;">{r['cum_distance']:.1f} km</td>
                    <td class="text-right" style="color: #64748b;">{r['monthly_target']:.0f} km</td>
                    <td class="text-center"><span class="cat-pill cat-green">{r['pct_monthly']:.1f}%</span></td>
                </tr>
            """

        # 2. Surplus Distance (Top 10)
        for r in matched_runners:
            r["surplus_km"] = round(r["cum_distance"] - r["monthly_target"], 2)
        top_surplus = sorted([m for m in mtd_active if m["surplus_km"] > 0], key=lambda x: (x["surplus_km"], x["cum_distance"]), reverse=True)[:10]
        surplus_rows = ""
        for idx, r in enumerate(top_surplus):
            rank_str = medals[idx]
            surplus_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700; font-size: 11px;">{rank_str}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-right" style="font-weight: 800;"><span class="cat-pill cat-purple">+{r['surplus_km']:.1f} km</span></td>
                    <td class="text-right" style="font-weight: 600;">{r['cum_distance']:.1f} km</td>
                    <td class="text-right" style="color: #64748b;">{r['monthly_target']:.0f} km</td>
                </tr>
            """

        # 3. Run Frequency (Top 10)
        top_freq = sorted(mtd_active, key=lambda x: (x["cum_runs"], x["cum_distance"]), reverse=True)[:10]
        freq_rows = ""
        for idx, r in enumerate(top_freq):
            rank_str = medals[idx]
            avg_per_run = (r["cum_distance"] / r["cum_runs"]) if r["cum_runs"] > 0 else 0.0
            freq_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700; font-size: 11px;">{rank_str}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-center" style="font-weight: 800;"><span class="cat-pill cat-blue">{r['cum_runs']} runs</span></td>
                    <td class="text-right" style="font-weight: 600;">{r['cum_distance']:.1f} km</td>
                    <td class="text-right" style="color: #64748b;">{avg_per_run:.1f} km/run</td>
                </tr>
            """

        # 4. Single Longest Run (Top 10)
        top_longest = sorted(mtd_active, key=lambda x: (x.get("cum_longest", 0.0), x["cum_distance"]), reverse=True)[:10]
        longest_rows = ""
        for idx, r in enumerate(top_longest):
            rank_str = medals[idx]
            l_km = r.get("cum_longest", 0.0)
            if l_km >= 80.0:
                milestone = "50-Mile Ultra 🏅"
            elif l_km >= 42.195:
                milestone = "Marathon+ 🏃"
            elif l_km >= 21.097:
                milestone = "Half Marathon 🏃"
            else:
                milestone = f"{l_km:.1f} km"
            longest_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700; font-size: 11px;">{rank_str}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-right" style="font-weight: 800;"><span class="cat-pill cat-amber">{l_km:.1f} km</span></td>
                    <td class="text-center" style="font-weight: 600; font-size: 9px; color: #475569; white-space: nowrap;">{milestone}</td>
                    <td class="text-right" style="color: #64748b; white-space: nowrap;">{r['cum_distance']:.1f} km</td>
                </tr>
            """

        # 5. Speed (Pace) (Top 10, min 20 km)
        speed_valid = [m for m in mtd_active if m.get("cum_pace_s", 99999) < 99999 and m.get("cum_distance", 0) >= 20.0]
        top_speed = sorted(speed_valid, key=lambda x: x["cum_pace_s"])[:10]
        speed_rows = ""
        for idx, r in enumerate(top_speed):
            rank_str = medals[idx]
            speed_rows += f"""
                <tr>
                    <td class="text-center" style="font-weight: 700; font-size: 11px;">{rank_str}</td>
                    <td style="font-weight: 600;">{r['registered_name']}</td>
                    <td class="text-center" style="font-weight: 800;"><span class="cat-pill cat-speed">⚡️ {r['cum_pace_str']}</span></td>
                    <td class="text-right" style="font-weight: 600; white-space: nowrap;">{r['cum_distance']:.1f} km</td>
                    <td class="text-center" style="color: #64748b; white-space: nowrap;">{r['cum_runs']} runs</td>
                </tr>
            """

        category_leaderboards_html = f"""
    <div class="page-break"></div>
    <div class="section-title" style="margin-top: 4px; margin-bottom: 8px; font-size: 13px;">🏆 SWIFTEMBER 2026 • CATEGORY LEADERBOARDS (TOP 10)</div>
    
    <div class="category-grid">
        <!-- Row 1: Total Distance, Surplus Distance, Run Frequency -->
        <div class="cat-card cat-card-3col">
            <div class="cat-card-header">
                <span class="cat-card-title">👑 Total Distance</span>
                <span class="cat-card-badge">Overall KM</span>
            </div>
            <table class="cat-table">
                <thead>
                    <tr>
                        <th class="text-center" style="width: 28px;">#</th>
                        <th>Athlete</th>
                        <th class="text-right">Logged</th>
                        <th class="text-right">Target</th>
                        <th class="text-center">Goal %</th>
                    </tr>
                </thead>
                <tbody>
                    {dist_rows}
                </tbody>
            </table>
        </div>

        <div class="cat-card cat-card-3col">
            <div class="cat-card-header">
                <span class="cat-card-title">🚀 Surplus Distance</span>
                <span class="cat-card-badge">+KM Above Goal</span>
            </div>
            <table class="cat-table">
                <thead>
                    <tr>
                        <th class="text-center" style="width: 28px;">#</th>
                        <th>Athlete</th>
                        <th class="text-right">Surplus</th>
                        <th class="text-right">Total</th>
                        <th class="text-right">Target</th>
                    </tr>
                </thead>
                <tbody>
                    {surplus_rows}
                </tbody>
            </table>
        </div>

        <div class="cat-card cat-card-3col">
            <div class="cat-card-header">
                <span class="cat-card-title">👟 Run Frequency</span>
                <span class="cat-card-badge">Most Runs Logged</span>
            </div>
            <table class="cat-table">
                <thead>
                    <tr>
                        <th class="text-center" style="width: 28px;">#</th>
                        <th>Athlete</th>
                        <th class="text-center">Runs</th>
                        <th class="text-right">Total</th>
                        <th class="text-right">Avg/Run</th>
                    </tr>
                </thead>
                <tbody>
                    {freq_rows}
                </tbody>
            </table>
        </div>

        <!-- Row 2: Single Longest Run, Speed (Pace) -->
        <div class="cat-card cat-card-2col">
            <div class="cat-card-header">
                <span class="cat-card-title">🦅 Single Longest Run</span>
                <span class="cat-card-badge">Biggest Single Effort</span>
            </div>
            <table class="cat-table">
                <thead>
                    <tr>
                        <th class="text-center" style="width: 26px;">#</th>
                        <th>Athlete</th>
                        <th class="text-right">Longest Run</th>
                        <th class="text-center">Milestone</th>
                        <th class="text-right">Total Dist</th>
                    </tr>
                </thead>
                <tbody>
                    {longest_rows}
                </tbody>
            </table>
        </div>

        <div class="cat-card cat-card-2col">
            <div class="cat-card-header">
                <span class="cat-card-title">⚡️ Speed (Pace)</span>
                <span class="cat-card-badge">Weighted Avg Pace (≥ 20km)</span>
            </div>
            <table class="cat-table">
                <thead>
                    <tr>
                        <th class="text-center" style="width: 26px;">#</th>
                        <th>Athlete</th>
                        <th class="text-center">Avg Pace</th>
                        <th class="text-right">Total Dist</th>
                        <th class="text-center">Runs</th>
                    </tr>
                </thead>
                <tbody>
                    {speed_rows}
                </tbody>
            </table>
        </div>
    </div>

    <!-- Club Finale Celebration Banner -->
    <div class="finale-banner">
        <div class="finale-banner-header">
            <span class="finale-star">🎉</span>
            <span class="finale-title">SWIFTEMBER 2026 CHALLENGE COMPLETE!</span>
            <span class="finale-star">🎉</span>
        </div>
        <div class="finale-banner-sub">Huge congratulations to all 66 Birmingham Swifts runners for an incredible month of dedication, endurance, and community spirit!</div>
        <div class="finale-stats-grid">
            <div class="finale-stat-item">
                <div class="finale-stat-num">{total_cum_logged:,.1f} km</div>
                <div class="finale-stat-lbl">Total Distance Smashed ({pct_total_month:.1f}%)</div>
            </div>
            <div class="finale-stat-item">
                <div class="finale-stat-num">{total_cum_runs}</div>
                <div class="finale-stat-lbl">Total Runs Logged</div>
            </div>
            <div class="finale-stat-item">
                <div class="finale-stat-num">{total_cum_elev:,} m</div>
                <div class="finale-stat-lbl">Total Elevation Gain</div>
            </div>
            <div class="finale-stat-item">
                <div class="finale-stat-num">{len(goal_achievers)} / {len(matched_runners)}</div>
                <div class="finale-stat-lbl">Goal Achievers ({pct_achievers:.1f}%)</div>
            </div>
        </div>
    </div>
    <div class="footer">
        {footer_text} • Page 3 of 5
    </div>
        """

    final_shoutouts_html = ""
    if is_final:
        finishers = load_final_finishers()
        if finishers:
            split_idx = 12 if len(finishers) >= 23 else 11
            cohort_metadata = [
                {
                    "part": 1,
                    "badge": "📊 PART 1 • CATEGORY LEADERS, SURPLUS ACHIEVEMENTS & VOLUME BUILDS",
                    "subtitle": f"Selective Highlights #1 – #{split_idx} • Notable Individual Performances & Milestone Metrics",
                    "page_num": 4,
                    "batch": finishers[:split_idx],
                    "start_i": 0
                },
                {
                    "part": 2,
                    "badge": "🏅 PART 2 • ENDURANCE TITANS, MARATHON MILESTONES & SPECIAL SPOTLIGHTS",
                    "subtitle": f"Selective Highlights #{split_idx + 1} – #{len(finishers)} • High-Elevation Records, Major Debuts & Medical Comebacks",
                    "page_num": 5,
                    "batch": finishers[split_idx:],
                    "start_i": split_idx
                }
            ]

            parts_html_list = []
            for meta in cohort_metadata:
                batch = meta["batch"]
                start_i = meta["start_i"]
                
                cards_html = ""
                for c_idx, f in enumerate(batch):
                    spotlight_num = start_i + c_idx + 1
                    rk = f["rank"]
                    rank_str = f"Rank #{rk}"
                    elev_str = f"{f['total_elev_m']:,} m elev" if f.get('total_elev_m', 0) > 0 else "-- elev"
                    longest_str = f"{f['longest_run_km']:.1f} km max" if f.get('longest_run_km', 0) > 0 else "-"
                    pace_str = f"⚡️ {f['avg_pace']}" if f.get('avg_pace') and f['avg_pace'] != "--" else "Pace: --"
                    surplus_txt = f"+{f['surplus_km']:.1f} km" if f.get('surplus_km', 0) > 0 else "Goal Hit"
                    
                    cards_html += f"""
                    <div class="finisher-card">
                        <div class="finisher-card-header">
                            <div class="finisher-name-wrap">
                                <span class="finisher-rank">{rank_str}</span>
                                <span class="finisher-name">{f['name']}</span>
                            </div>
                            <span class="finisher-badge-pct">{f['total_km']:.1f} / {f['target_km']:.0f} km ({f['pct_achieved']:.1f}%)</span>
                        </div>
                        <div class="finisher-tag">{f['tag']}</div>
                        <div class="finisher-msg">{f['shoutout']}</div>
                        <div class="finisher-stats-bar">
                            <span>🏃 {f['total_runs']} runs • 📏 {f['total_km']:.1f} km ({surplus_txt}) • ⛰ {elev_str}</span>
                            <span>🏅 {longest_str} • {pace_str}</span>
                        </div>
                    </div>
                    """
                
                part_page_html = f"""
                <div class="page-break"></div>
                <div class="finisher-page-header">
                    <div>
                        <div class="finisher-page-title">
                            <span>🏆 SWIFTEMBER 2026 • SELECTED HIGHLIGHTS & NOTABLE MILESTONES</span>
                            <span class="finisher-page-pill">{meta['badge']}</span>
                        </div>
                        <div class="finisher-page-sub">{meta['subtitle']}</div>
                    </div>
                    <div style="text-align: right;">
                        <span class="finisher-page-counter">Page {meta['page_num']} of 5</span>
                    </div>
                </div>
                <div class="finishers-grid">
                    {cards_html}
                </div>
                <div class="footer">
                    {footer_text} • Page {meta['page_num']} of 5
                </div>
                """
                parts_html_list.append(part_page_html)

            final_shoutouts_html = "".join(parts_html_list)

    # Weekly leaderboard section (omitted for final report)
    weekly_leaderboard_html = ""
    if not is_final:
        weekly_leaderboard_html = f"""
    <div class="section-title">🎯 WEEKLY ACHIEVEMENT LEADERBOARD</div>
    <table class="weekly-table">
        <thead>
            <tr>
                <th class="text-center" style="width: 34px;">Rank</th>
                <th>Runner Name</th>
                <th class="text-right">Week Logged</th>
                <th class="text-right">Weekly Goal</th>
                <th class="text-center">Weekly Goal %</th>
                <th class="text-right">Elevation</th>
                <th class="text-center">Status</th>
            </tr>
        </thead>
        <tbody>
            {target_rows}
        </tbody>
    </table>
    {fastest_pacers_html}
    {middle_section}
        """

    # Main table header
    main_section_title = "🏆 SWIFTEMBER 2026 FINAL LEADERBOARD & FULL RESULTS" if is_final else "📋 FULL SWIFTEMBER REPORT"
    if is_final:
        main_table_header = """
            <tr>
                <th class="text-center" style="width: 28px;">#</th>
                <th>Participant Name</th>
                <th class="text-right" style="width: 80px;">Monthly Target</th>
                <th class="text-right" style="width: 85px;">Total Logged</th>
                <th class="text-center" style="width: 145px;">Challenge Progress</th>
                <th class="text-center" style="width: 145px;">Final Status</th>
            </tr>
        """
    else:
        main_table_header = """
            <tr>
                <th class="text-center" style="width: 25px;">#</th>
                <th>Participant Name</th>
                <th class="text-right">Monthly Pledge</th>
                <th class="text-right">Total Logged (MTD)</th>
                <th class="text-right">Remaining</th>
                <th class="text-center">Monthly Progress</th>
                <th class="text-center">Challenge Status</th>
            </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{doc_title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @page {{ size: A4; margin: 8mm 8mm; }}
        * {{ box-sizing: border-box; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #1e293b; background-color: #ffffff; line-height: 1.35; font-size: {body_font}; margin: 0; padding: 0;
        }}
        .header {{
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
            color: #ffffff; padding: 10px 14px; border-radius: 8px; margin-bottom: 7px;
            display: flex; align-items: center; justify-content: flex-start;
        }}
        .header-left {{ display: flex; align-items: center; gap: 12px; width: 100%; }}
        .header-title h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px; }}
        .header-title p {{ margin: 2px 0 0 0; font-size: 10.5px; color: #cbd5e1; font-weight: 400; }}
        .section-title {{
            font-size: 12px; font-weight: 700; color: #0f172a; margin: 8px 0 5px 0;
            display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 3px;
        }}
        .superlatives-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 7px; }}
        .super-card {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0; border-top: 3px solid #6366f1; border-radius: 7px; padding: 5px 3px; text-align: center;
        }}
        .super-icon {{ font-size: 15px; margin-bottom: 1px; }}
        .super-award {{ font-size: {super_award_font}; font-weight: 800; color: #334155; text-transform: uppercase; letter-spacing: 0.2px; margin-bottom: 1px; line-height: 1.15; }}
        .super-sub {{ font-size: {super_sub_font}; font-weight: 600; color: #64748b; margin-bottom: 2px; }}
        .super-winner {{ font-size: {super_winner_font}; font-weight: 800; color: #1e1b4b; margin-bottom: 2px; line-height: 1.15; }}
        .super-stat {{ font-size: {super_stat_font}; font-weight: 700; color: #4338ca; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 7px; margin-bottom: 7px; }}
        .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 7px; padding: 6px 8px; text-align: center; }}
        .metric-val {{ font-size: {metric_val_font}; font-weight: 800; color: #0f172a; margin-bottom: 1px; }}
        .metric-label {{ font-size: {metric_lbl_font}; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-sub {{ font-size: {metric_sub_font}; color: #3b82f6; margin-top: 1px; font-weight: 500; }}
        
        thead {{ display: table-header-group; }}
        tr {{ page-break-inside: avoid; }}
        table {{ width: 100%; border-collapse: collapse; font-size: {table_font}; margin-bottom: 5px; }}
        th {{
            background: #f1f5f9; color: #334155; font-weight: 700; text-transform: uppercase;
            font-size: {th_font}; letter-spacing: 0.4px; padding: {th_pad}; border-top: 1px solid #cbd5e1; border-bottom: 2px solid #cbd5e1; text-align: left;
        }}
        td {{ padding: {td_pad}; border-bottom: 1px solid #f1f5f9; color: #1e293b; vertical-align: middle; }}
        tr:nth-child(even) td {{ background-color: #fafafa; }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .status-badge {{ display: inline-block; padding: {badge_pad}; border-radius: 10px; font-size: {badge_font}; font-weight: 700; white-space: nowrap; }}
        .badge-ahead {{ background: #dcfce7; color: #15803d; }}
        .badge-track {{ background: #dbeafe; color: #1d4ed8; }}
        .badge-slight {{ background: #fef9c3; color: #a16207; }}
        .badge-behind {{ background: #fee2e2; color: #b91c1c; }}
        .badge-zero {{ background: #f1f5f9; color: #64748b; }}
        table.weekly-table {{ font-size: 16px; }}
        table.weekly-table th {{
            font-size: 12px;
            padding: 5.5px 8px;
            letter-spacing: 0.5px;
        }}
        table.weekly-table td {{
            padding: 4.5px 8px;
            font-size: 16px;
        }}
        table.weekly-table .progress-val {{
            font-size: 16px;
        }}
        table.weekly-table .progress-bar-container {{
            width: 75px;
            height: 6px;
        }}
        table.weekly-table .status-badge {{
            font-size: 12px;
            padding: 3.5px 10px;
        }}
        table.full-table {{ font-size: 16px; width: 100%; border-collapse: collapse; margin-bottom: 5px; }}
        table.full-table th {{
            font-size: 12.5px;
            padding: 4px 6px;
            letter-spacing: 0.4px;
            background: #f1f5f9;
            color: #334155;
            font-weight: 700;
            border-top: 1px solid #cbd5e1;
            border-bottom: 2px solid #cbd5e1;
        }}
        table.full-table td {{
            padding: 1.5px 6px;
            font-size: 16px;
            line-height: 1.15;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
            white-space: nowrap;
        }}
        table.full-table .progress-cell {{
            flex-direction: row;
            justify-content: center;
            align-items: center;
            gap: 6px;
        }}
        table.full-table .progress-val {{
            font-size: 14px;
            font-weight: 700;
            line-height: 1.1;
            min-width: 48px;
            text-align: right;
        }}
        table.full-table .progress-bar-container {{
            width: 70px;
            height: 6px;
        }}
        table.full-table .status-badge {{
            font-size: 12.5px;
            padding: 1.5px 7px;
        }}
        table.fastest-table {{ font-size: 15px; width: 100%; border-collapse: collapse; margin-bottom: 6px; }}
        table.fastest-table th {{
            font-size: 12px;
            padding: 5px 8px;
            letter-spacing: 0.5px;
            background: linear-gradient(180deg, #f8fafc 0%, #edf2f7 100%);
            color: #334155;
            font-weight: 700;
            text-transform: uppercase;
            border-top: 1px solid #cbd5e1;
            border-bottom: 2px solid #cbd5e1;
        }}
        table.fastest-table td {{
            padding: 4px 8px;
            font-size: 15px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
            vertical-align: middle;
        }}
        table.fastest-table tr:nth-child(even) td {{ background-color: #fafafa; }}
        table.fastest-table .status-badge {{
            font-size: 11.5px;
            padding: 2.5px 8px;
        }}
        .pace-badge {{
            display: inline-block;
            background: #ede9fe;
            color: #5b21b6;
            font-weight: 800;
            padding: 2.5px 8px;
            border-radius: 6px;
            font-size: 14px;
            letter-spacing: 0.2px;
        }}
        .pace-badge.rank-1 {{
            background: #fef3c7;
            color: #92400e;
            border: 1px solid #fde68a;
            box-shadow: 0 1px 3px rgba(245, 158, 11, 0.2);
        }}
        .progress-cell {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 2px;
            margin: 0 auto;
        }}
        .progress-val {{
            font-size: {prog_val_font};
            font-weight: 700;
            line-height: 1.1;
            text-align: center;
        }}
        .progress-bar-container {{
            width: {prog_bar_w};
            background: #e2e8f0;
            border-radius: 4px;
            height: {prog_bar_h};
            overflow: hidden;
            display: block;
        }}
        .progress-bar {{ height: 100%; background: #3b82f6; border-radius: 4px; }}
        .progress-bar.green {{ background: #22c55e; }}
        .progress-bar.blue {{ background: #3b82f6; }}
        .progress-bar.yellow {{ background: #eab308; }}
        .progress-bar.red {{ background: #ef4444; }}
        .shoutouts-grid {{
            display: flex;
            flex-direction: column;
            gap: {shout_grid_gap};
            margin-bottom: 5px;
        }}
        .shoutout-card {{
            background: linear-gradient(135deg, #f0fdf4 0%, #e0f2fe 100%);
            border: 1px solid #bae6fd;
            border-left: 4.5px solid #0284c7;
            border-radius: 7px;
            padding: {shout_card_pad};
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }}
        .shoutout-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2px;
            gap: 8px;
        }}
        .shoutout-name {{
            font-size: {shout_name_font};
            font-weight: 700;
            color: #0369a1;
        }}
        .shoutout-tag {{
            background: #0284c7;
            color: #ffffff;
            font-size: {shout_tag_font};
            font-weight: 700;
            padding: 2.5px 8px;
            border-radius: 6px;
            white-space: nowrap;
        }}
        .shoutout-msg {{
            font-size: {shout_msg_font};
            color: #334155;
            line-height: 1.36;
        }}
        .shoutouts-footer {{
            text-align: center;
            font-size: {shout_footer_font};
            font-weight: 600;
            color: #64748b;
            font-style: italic;
            margin-top: 6px;
            margin-bottom: 4px;
        }}
        /* Berlin Marathon Special Showcase */
        .berlin-container {{
            margin: 0;
            padding: 0;
        }}
        .berlin-hero {{
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #312e81 100%);
            border-radius: 9px;
            overflow: hidden;
            color: #ffffff;
            margin-bottom: {berlin_hero_mb};
            box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
            border: 1px solid #334155;
        }}
        .berlin-flag-stripe {{
            height: 6px;
            background: linear-gradient(90deg, #000000 0%, #000000 33.3%, #dc2626 33.3%, #dc2626 66.6%, #eab308 66.6%, #eab308 100%);
            border-bottom: 1px solid rgba(255, 255, 255, 0.25);
        }}
        .berlin-hero-content {{
            padding: {berlin_hero_pad};
        }}
        .berlin-top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;
        }}
        .berlin-pill {{
            background: #dc2626;
            color: #ffffff;
            font-size: 11.5px;
            font-weight: 800;
            padding: 3px 9px;
            border-radius: 5px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }}
        .berlin-date-pill {{
            background: rgba(255, 255, 255, 0.15);
            color: #fde047;
            font-size: 11.5px;
            font-weight: 700;
            padding: 3px 9px;
            border-radius: 5px;
            letter-spacing: 0.3px;
        }}
        .berlin-headline {{
            margin: 0 0 4px 0;
            font-size: {berlin_headline_font};
            font-weight: 800;
            letter-spacing: -0.4px;
            color: #ffffff;
            line-height: 1.2;
        }}
        .berlin-intro {{
            margin: 0;
            font-size: {berlin_intro_font};
            color: #cbd5e1;
            line-height: 1.35;
        }}
        .berlin-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: {berlin_grid_gap};
            margin-bottom: 6px;
        }}
        .berlin-card {{
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #cbd5e1;
            border-left: 4.5px solid #2563eb;
            border-radius: 7px;
            padding: {berlin_card_pad};
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }}
        .berlin-card-full {{
            grid-column: span 2;
            background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
            border-left: 4.5px solid #d97706;
        }}
        .berlin-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 2px;
            gap: 8px;
        }}
        .berlin-card-name {{
            font-size: {berlin_name_font};
            font-weight: 700;
            color: #1e1b4b;
        }}
        .berlin-card-tag {{
            background: #e0f2fe;
            color: #0369a1;
            font-size: {berlin_tag_font};
            font-weight: 700;
            padding: 2.5px 8px;
            border-radius: 5px;
            white-space: nowrap;
            border: 1px solid #bae6fd;
        }}
        .berlin-card-msg {{
            font-size: {berlin_msg_font};
            color: #334155;
            line-height: 1.34;
        }}
        .berlin-footer {{
            text-align: center;
            font-size: {berlin_footer_font};
            font-weight: 600;
            color: #475569;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            padding: {berlin_footer_pad};
            line-height: 1.35;
        }}
        .pride-runners-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px 8px;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed #bae6fd;
        }}
        .pride-runner-pill {{
            background: #ffffff;
            border: 1px solid #bfdbfe;
            color: #1e3a8a;
            font-size: {pride_pill_font};
            font-weight: 700;
            padding: {pride_pill_pad};
            border-radius: 6px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
            white-space: nowrap;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }}
        /* Category Leaderboards (Top 5) & Finale Styling */
        .category-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 8px;
            margin-top: 6px;
            margin-bottom: 8px;
        }}
        .cat-card {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0;
            border-top: 3px solid #4338ca;
            border-radius: 8px;
            padding: 7px 9px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
            display: flex;
            flex-direction: column;
        }}
        .cat-card-3col {{ grid-column: span 2; }}
        .cat-card-2col {{ grid-column: span 3; }}
        .cat-card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 5px;
            padding-bottom: 4px;
            border-bottom: 1.5px solid #e2e8f0;
        }}
        .cat-card-title {{
            font-size: 11.5px;
            font-weight: 800;
            color: #0f172a;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        .cat-card-badge {{
            font-size: 8.5px;
            font-weight: 700;
            padding: 1.5px 6px;
            border-radius: 4px;
            background: #e0e7ff;
            color: #3730a3;
        }}
        table.cat-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 10px;
            margin-bottom: 0;
        }}
        table.cat-table th {{
            font-size: 8.5px;
            font-weight: 700;
            color: #475569;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            padding: 2.5px 3.5px;
            border-top: none;
            border-bottom: 1.5px solid #cbd5e1;
            background: transparent;
        }}
        table.cat-table td {{
            padding: 2.0px 3.5px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
            vertical-align: middle;
            font-size: 9.6px;
            line-height: 1.2;
        }}
        table.cat-table tr:nth-child(even) td {{ background-color: #fafafa; }}
        table.cat-table tr:last-child td {{ border-bottom: none; }}
        .cat-pill {{
            display: inline-block;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 4px;
            font-size: 9.5px;
            white-space: nowrap;
        }}
        .cat-green {{ background: #dcfce7; color: #15803d; }}
        .cat-purple {{ background: #f3e8ff; color: #6b21a8; }}
        .cat-blue {{ background: #dbeafe; color: #1e40af; }}
        .cat-amber {{ background: #fef3c7; color: #92400e; }}
        .cat-speed {{ background: #ede9fe; color: #5b21b6; }}

        /* Club Finale Celebration Banner */
        .finale-banner {{
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%);
            border-radius: 8px;
            padding: 10px 16px;
            color: #ffffff;
            text-align: center;
            margin-top: 6px;
            margin-bottom: 6px;
            border: 1px solid #4338ca;
            box-shadow: 0 4px 12px rgba(30, 27, 75, 0.12);
        }}
        .finale-banner-header {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 0.5px;
            color: #fde047;
            margin-bottom: 2px;
        }}
        .finale-banner-sub {{
            font-size: 9.5px;
            color: #cbd5e1;
            margin-bottom: 7px;
        }}
        .finale-stats-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
        }}
        .finale-stat-item {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 6px;
            padding: 5px 4px;
        }}
        .finale-stat-num {{
            font-size: 13.5px;
            font-weight: 800;
            color: #ffffff;
        }}
        .finale-stat-lbl {{
            font-size: 8px;
            font-weight: 600;
            color: #93c5fd;
            text-transform: uppercase;
            letter-spacing: 0.3px;
            margin-top: 1px;
        }}
        /* Finisher Roll of Honor Section */
        .finisher-page-header {{
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%);
            border-radius: 7px;
            padding: 4px 12px;
            color: #ffffff;
            margin-top: 1px;
            margin-bottom: 4px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .finisher-page-title {{
            font-size: 12px;
            font-weight: 800;
            letter-spacing: 0.3px;
            display: flex;
            align-items: center;
            gap: 7px;
        }}
        .finisher-page-sub {{
            font-size: 9.5px;
            color: #cbd5e1;
            font-weight: 500;
            margin-top: 1px;
        }}
        .finisher-page-pill {{
            background: rgba(255, 255, 255, 0.15);
            color: #fde047;
            font-size: 9px;
            font-weight: 700;
            padding: 1.5px 7px;
            border-radius: 4px;
            white-space: nowrap;
        }}
        .finisher-page-counter {{
            font-size: 10px;
            font-weight: 700;
            color: #93c5fd;
            white-space: nowrap;
        }}
        .finishers-grid {{
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            margin-bottom: 2px;
        }}
        .finisher-card {{
            width: 49.3%;
            display: inline-flex;
            flex-direction: column;
            justify-content: space-between;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #cbd5e1;
            border-left: 3.5px solid #4338ca;
            border-radius: 6px;
            padding: 4.5px 8px;
            margin-bottom: 4.5px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
            page-break-inside: avoid;
            break-inside: avoid;
            box-sizing: border-box;
            min-height: 70px;
        }}
        .finisher-card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5px;
            gap: 6px;
        }}
        .finisher-name-wrap {{
            display: flex;
            align-items: center;
            gap: 5px;
            overflow: hidden;
        }}
        .finisher-rank {{
            font-size: 10.5px;
            font-weight: 800;
            color: #3730a3;
            background: #e0e7ff;
            padding: 1.5px 5px;
            border-radius: 3.5px;
            line-height: 1.1;
            white-space: nowrap;
        }}
        .finisher-name {{
            font-size: 13.5px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1.15;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .finisher-badge-pct {{
            font-size: 10px;
            font-weight: 700;
            color: #15803d;
            background: #dcfce7;
            padding: 1.5px 4.5px;
            border-radius: 3.5px;
            white-space: nowrap;
        }}
        .finisher-tag {{
            font-size: 11.5px;
            font-weight: 700;
            color: #0284c7;
            margin-bottom: 2px;
            line-height: 1.22;
        }}
        .finisher-msg {{
            font-size: 14px;
            color: #334155;
            line-height: 1.30;
            margin-bottom: 3px;
            flex-grow: 1;
        }}
        .finisher-stats-bar {{
            font-size: 9.5px;
            color: #64748b;
            font-weight: 600;
            border-top: 1px dashed #e2e8f0;
            padding-top: 2.5px;
            display: flex;
            justify-content: space-between;
            white-space: nowrap;
        }}
        .page-break {{ page-break-before: always; }}
        .footer {{ font-size: 8.5px; color: #64748b; text-align: center; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 4px; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            {logo_html}
            <div class="header-title">
                <h1>🏳️‍🌈 SWIFTEMBER 2026</h1>
                <p>Birmingham Swifts — {header_subtitle}</p>
            </div>
        </div>
    </div>

    <div class="section-title">{hero_section_title}</div>
    <div class="superlatives-grid">
        {hero_cards_html}
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-val">{card1_val}</div>
            <div class="metric-label">{card1_lbl}</div>
            <div class="metric-sub">{card1_sub}</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{card2_val}</div>
            <div class="metric-label">{card2_lbl}</div>
            <div class="metric-sub">{card2_sub}</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{card3_val}</div>
            <div class="metric-label">{card3_lbl}</div>
            <div class="metric-sub">{card3_sub}</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{card4_val}</div>
            <div class="metric-label">{card4_lbl}</div>
            <div class="metric-sub">{card4_sub}</div>
        </div>
    </div>

    {weekly_leaderboard_html}

    <div class="section-title">{main_section_title}</div>
    <table class="full-table">
        <thead>
            {main_table_header}
        </thead>
        <tbody>
            {roster_rows}
        </tbody>
    </table>

    {category_leaderboards_html}

    {final_shoutouts_html}

    {"" if is_final else f'<div class="footer">{footer_text}</div>'}
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Generate Swiftember Weekly PDF & Markdown Report")
    parser.add_argument("-i", "--input", help="Path to raw Strava leaderboard data text file (or stdin if omitted)")
    parser.add_argument("-w", "--week", type=int, default=1, help="Week number (1, 2, 3, 4, 5). Default: 1")
    parser.add_argument("--final", action="store_true", help="Generate final challenge report from all data")
    parser.add_argument("-o", "--output-pdf", help="Output PDF file path (default: ~/Downloads/Swiftember_2026_Final_Report.pdf)")
    parser.add_argument("-t", "--title-sub", default="Official Swiftember Report", help="Subtitle under badge in header")
    parser.add_argument("-f", "--font-size", choices=["large", "compact"], default="large", help="Font size preset: 'large' (default bigger fonts) or 'compact'")
    args = parser.parse_args()

    is_final = args.final or (args.week >= 5)
    week_num = 5 if is_final else args.week

    roster = load_roster()
    aliases = load_aliases()

    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = f.read()
    else:
        # Check if weekly input file exists in data/
        week_input_file = os.path.join(DATA_DIR, f"week_{week_num}_strava.txt")
        mock_file = os.path.join(BASE_DIR, "mock_strava_data.txt")
        if os.path.exists(week_input_file):
            print(f"[INFO] Using data file: {week_input_file}")
            with open(week_input_file, "r", encoding="utf-8") as f:
                raw_data = f.read()
        elif os.path.exists(mock_file):
            print(f"[INFO] Using data file: {mock_file}")
            with open(mock_file, "r", encoding="utf-8") as f:
                raw_data = f.read()
        else:
            print("[ERROR] No input file provided and mock_strava_data.txt not found.")
            sys.exit(1)

    historical_stats = load_historical_stats(up_to_week=week_num)
    strava_entries = parse_strava_table(raw_data)
    matched_runners = process_swiftember_data(strava_entries, roster, aliases, week_num=week_num, historical_stats=historical_stats, is_final=is_final)

    # Save current week stats to data/week_{week_num}_stats.json
    save_week_stats(week_num, matched_runners)

    # Generate HTML
    html_content = generate_html_report(matched_runners, week_num=week_num, badge_subtitle=args.title_sub, font_size=args.font_size, is_final=is_final)
    
    html_filename = "temp_report_final.html" if is_final else f"temp_report_week{week_num}.html"
    html_path = os.path.join(BASE_DIR, html_filename)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Output PDF
    downloads_dir = os.path.expanduser("~/Downloads")
    default_pdf_name = "Swiftember_2026_Final_Report.pdf" if is_final else f"Swiftember_2026_Week{week_num}_Report.pdf"
    default_pdf_path = os.path.join(downloads_dir, default_pdf_name)
    pdf_path = args.output_pdf if args.output_pdf else default_pdf_path

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    if is_final:
        # Chromium print engine can hang when printing a massive HTML document combining large paged tables with multi-page CSS grids.
        # Splitting into Part 1 (Pages 1-2: Table), Part 2 (Page 3: Category Leaderboards), and Part 3 (Pages 4-5: Highlights)
        # and merging via macOS PDFKit guarantees flawless 5-page rendering in under 10 seconds.
        idx_cat = html_content.find("🏆 SWIFTEMBER 2026 • CATEGORY LEADERBOARDS")
        idx_shout = html_content.find('<div class="finisher-page-header">')
        if idx_cat != -1 and idx_shout != -1:
            head_end = html_content.find("</head>")
            head = html_content[:head_end + 7] + "\n<body>\n"

            idx_pb_cat = html_content.rfind('<div class="page-break"></div>', 0, idx_cat)
            part1_body = html_content[:idx_pb_cat if idx_pb_cat != -1 else idx_cat].strip()
            part1_html = part1_body + "\n</body>\n</html>"

            idx_pb_shout = html_content.rfind('<div class="page-break"></div>', 0, idx_shout)
            part2_body = html_content[idx_cat:idx_pb_shout if idx_pb_shout != -1 else idx_shout].strip()
            part2_html = head + part2_body + "\n</body>\n</html>"

            part3_body = html_content[idx_shout:html_content.rfind("</body>")].strip()
            part3_html = head + part3_body + "\n</body>\n</html>"

            p1_html_path = os.path.join(BASE_DIR, "temp_report_final_p1_2.html")
            p2_html_path = os.path.join(BASE_DIR, "temp_report_final_p3.html")
            p3_html_path = os.path.join(BASE_DIR, "temp_report_final_p4_5.html")
            p1_pdf_path = "/tmp/swiftember_final_p1_2.pdf"
            p2_pdf_path = "/tmp/swiftember_final_p3.pdf"
            p3_pdf_path = "/tmp/swiftember_final_p4_5.pdf"

            with open(p1_html_path, "w", encoding="utf-8") as f:
                f.write(part1_html)
            with open(p2_html_path, "w", encoding="utf-8") as f:
                f.write(part2_html)
            with open(p3_html_path, "w", encoding="utf-8") as f:
                f.write(part3_html)

            chrome_flags = ["--headless", "--disable-gpu", "--no-pdf-header-footer"]
            subprocess.run([chrome_bin, *chrome_flags, f"--print-to-pdf={p1_pdf_path}", f"file://{os.path.abspath(p1_html_path)}"], check=True)
            subprocess.run([chrome_bin, *chrome_flags, f"--print-to-pdf={p2_pdf_path}", f"file://{os.path.abspath(p2_html_path)}"], check=True)
            subprocess.run([chrome_bin, *chrome_flags, f"--print-to-pdf={p3_pdf_path}", f"file://{os.path.abspath(p3_html_path)}"], check=True)

            swift_merge_script = f"""
import Foundation
import PDFKit

guard let doc1 = PDFDocument(url: URL(fileURLWithPath: "{p1_pdf_path}")),
      let doc2 = PDFDocument(url: URL(fileURLWithPath: "{p2_pdf_path}")),
      let doc3 = PDFDocument(url: URL(fileURLWithPath: "{p3_pdf_path}")) else {{
    exit(1)
}}
for i in 0..<doc2.pageCount {{
    if let page = doc2.page(at: i) {{
        doc1.insert(page, at: doc1.pageCount)
    }}
}}
for i in 0..<doc3.pageCount {{
    if let page = doc3.page(at: i) {{
        doc1.insert(page, at: doc1.pageCount)
    }}
}}
doc1.write(to: URL(fileURLWithPath: "{pdf_path}"))
"""
            subprocess.run(["swift", "-e", swift_merge_script], check=True)
            for tmp_f in [p1_pdf_path, p2_pdf_path, p3_pdf_path]:
                if os.path.exists(tmp_f):
                    os.remove(tmp_f)
        else:
            chrome_cmd = [
                chrome_bin,
                "--headless",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--print-to-pdf={pdf_path}",
                f"file://{os.path.abspath(html_path)}"
            ]
            subprocess.run(chrome_cmd, check=True)
    else:
        chrome_cmd = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            f"file://{os.path.abspath(html_path)}"
        ]
        subprocess.run(chrome_cmd, check=True)

    report_title = "Final Challenge Results" if is_final else f"Week {week_num}"
    print(f"\n[SUCCESS] Swiftember {report_title} Report successfully generated!")
    print(f"📄 PDF Output: {pdf_path}")
    active_count = len([m for m in matched_runners if m['cum_distance'] > 0])
    achievers_count = len([m for m in matched_runners if m['cum_distance'] >= m['monthly_target']])
    print(f"📊 Processed: {len(matched_runners)} registered runners ({active_count} active MTD, {achievers_count} goal achievers)")

if __name__ == "__main__":
    main()
