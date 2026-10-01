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

def process_swiftember_data(strava_entries, roster, aliases, week_num=1, historical_stats=None):
    matched_runners = []
    unmatched_registered = list(roster.keys())
    expected_week_fraction = min(1.0, week_num / 4.0)
    
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
            existing = next((m for m in matched_runners if m["registered_name"] == found), None)
            if existing:
                existing["distance"] = round(existing["distance"] + s["distance"], 2)
                existing["runs"] += s["runs"]
                existing["longest"] = max(existing["longest"], s["longest"])
                existing["cum_distance"] = round(existing["cum_distance"] + s["distance"], 2)
                existing["cum_runs"] += s["runs"]
                
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
            
            this_dist = s["distance"]
            this_runs = s["runs"]
            
            cum_dist = prior_dist + this_dist
            cum_runs = prior_runs + this_runs
            
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
                
            # Cumulative pacing status for overall challenge (Full Swiftember Report)
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
                "longest": s["longest"],
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
                "cum_status": cum_status
            })
            
    # Process registered runners with 0 km recorded this week
    for r in unmatched_registered:
        monthly_target = roster[r]
        weekly_quota = monthly_target / 4.0
        
        hist_list = historical_stats.get(r, [])
        prior_dist = sum(h.get("distance", 0.0) for h in hist_list)
        prior_runs = sum(h.get("runs", 0) for h in hist_list)
        
        cum_dist = prior_dist
        cum_runs = prior_runs
        
        pct_monthly = (cum_dist / monthly_target) * 100.0 if monthly_target > 0 else 0.0
        pct_weekly = 0.0
        week_status = "⚪️ 0 km Logged"
        
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
            "cum_status": cum_status
        })
        
    return matched_runners

def generate_html_report(matched_runners, week_num=1, badge_subtitle="Official Swiftember Report", font_size="large"):
    # Target calculations
    weekly_active = [m for m in matched_runners if m["distance"] > 0]
    mtd_active = [m for m in matched_runners if m["cum_distance"] > 0]

    total_pledge = sum(m["monthly_target"] for m in matched_runners)
    total_cum_logged = sum(m["cum_distance"] for m in matched_runners)
    total_week_logged = sum(m["distance"] for m in matched_runners)
    expected_cum_target = total_pledge * min(1.0, week_num / 4.0)
    pct_total_month = (total_cum_logged / total_pledge) * 100.0 if total_pledge > 0 else 0.0
    pct_pace_rate = (total_cum_logged / expected_cum_target) * 100.0 if expected_cum_target > 0 else 0.0
    total_cum_runs = sum(m["cum_runs"] for m in matched_runners)
    total_week_runs = sum(m["runs"] for m in matched_runners)
    
    # Barriers between short, medium, and long distance runners decided by average target distance submitted by members
    avg_target = (total_pledge / len(matched_runners)) if matched_runners else 100.0
    short_barrier = round((avg_target * 0.5) / 25.0) * 25.0 if avg_target >= 40 else round(avg_target * 0.5)
    long_barrier = round(avg_target / 25.0) * 25.0 if avg_target >= 40 else round(avg_target)

    # 1. Rising Swift: Weekly goal achieved % most for short distance runners (<= short_barrier)
    short_active = [m for m in weekly_active if m["monthly_target"] <= short_barrier]
    rising_swift = max(short_active, key=lambda x: (x["pct_weekly"], x["distance"])) if short_active else None

    # 2. Goal Setter: Weekly goal achieved % most for medium distance runners (short_barrier < target <= long_barrier)
    med_active = [m for m in weekly_active if short_barrier < m["monthly_target"] <= long_barrier]
    pace_setter = max(med_active, key=lambda x: (x["pct_weekly"], x["distance"])) if med_active else None

    # 3. Road Warrior: Weekly goal achieved % most for long distance runners (> long_barrier)
    long_active = [m for m in weekly_active if m["monthly_target"] > long_barrier]
    road_warrior = max(long_active, key=lambda x: (x["pct_weekly"], x["distance"])) if long_active else None
    
    # Elev climber
    def parse_elev(e_str):
        nums = re.findall(r'\d+', e_str.replace(",", ""))
        return int(nums[0]) if nums else 0
    elev_runner = max(weekly_active, key=lambda x: parse_elev(x["elev"])) if weekly_active else None
    
    # Speed demon
    def parse_pace(p_str):
        m = re.match(r'(\d+):(\d+)', p_str)
        return int(m.group(1))*60 + int(m.group(2)) if m else 99999
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
    if fastest_rows:
        fastest_title = "⚡️ TOP 5 FASTEST PACERS (FINAL STRETCH)" if week_num >= 5 else "⚡️ TOP 5 FASTEST PACERS OF THE WEEK"
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

    # HTML Rows - Full Swiftember Report (Cumulative Challenge Tracking: Month Pledge, Total MTD, Remaining)
    all_sorted = sorted(matched_runners, key=lambda x: (x["cum_distance"] > 0, x["pct_monthly"], x["cum_distance"]), reverse=True)
    roster_rows = ""
    for i, r in enumerate(all_sorted, 1):
        pct_m = r['pct_monthly']
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

    # Build Shout-outs HTML
    shoutouts = load_shoutouts(week_num)
    shoutouts_html = ""
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
        super_award_font = "16px"
        super_sub_font = "9px"
        super_winner_font = "24px"
        super_stat_font = "10.5px"
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
        shout_name_font = "10px"
        shout_tag_font = "7.5px"
        shout_msg_font = "8.5px"
        shout_footer_font = "8.5px"
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

    card_dist_label = "Distance Logged (MTD)" if week_num > 1 else "Distance Logged"
    period_name = "Final Days" if week_num >= 5 else f"W{week_num}"
    card_dist_sub = f"{pct_total_month:.1f}% of Monthly Goal ({total_week_logged:,.1f} km in {period_name})" if week_num > 1 else f"{pct_total_month:.1f}% of Monthly Goal"
    card_active_label = "Active Runners (MTD)" if week_num > 1 else "Active Runners"
    card_active_sub = f"{total_cum_runs} Total Runs ({len(weekly_active)} active in {period_name})" if week_num > 1 else f"{total_cum_runs} Total Runs"

    if shoutouts_html:
        middle_section = f"""
        <div class="page-break"></div>
        {shoutouts_html}
        <div class="page-break"></div>
        """
    else:
        middle_section = """
        <div class="page-break"></div>
        """

    doc_title = "Swiftember 2026 - Final Month-End Wrap-Up Report" if week_num >= 5 else f"Swiftember 2026 - Week {week_num} Progress Report"
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{doc_title}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @page {{ size: A4; margin: 8.5mm 8.5mm; }}
        * {{ box-sizing: border-box; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #1e293b; background-color: #ffffff; line-height: 1.35; font-size: {body_font}; margin: 0; padding: 0;
        }}
        .header {{
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
            color: #ffffff; padding: 13px 16px; border-radius: 9px; margin-bottom: 11px;
            display: flex; align-items: center; justify-content: flex-start;
        }}
        .header-left {{ display: flex; align-items: center; gap: 14px; width: 100%; }}
        .header-title h1 {{ margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; display: flex; align-items: center; gap: 8px; }}
        .header-title p {{ margin: 3px 0 0 0; font-size: 11.5px; color: #cbd5e1; font-weight: 400; }}
        .section-title {{
            font-size: 13px; font-weight: 700; color: #0f172a; margin: 13px 0 7px 0;
            display: flex; align-items: center; gap: 6px; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px;
        }}
        .superlatives-grid {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 7px; margin-bottom: 11px; }}
        .super-card {{
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #e2e8f0; border-top: 3px solid #6366f1; border-radius: 8px; padding: 6px 4px; text-align: center;
        }}
        .super-icon {{ font-size: 16px; margin-bottom: 2px; }}
        .super-award {{ font-size: {super_award_font}; font-weight: 800; color: #334155; text-transform: uppercase; letter-spacing: 0.2px; margin-bottom: 2px; line-height: 1.15; }}
        .super-sub {{ font-size: {super_sub_font}; font-weight: 600; color: #64748b; margin-bottom: 3px; }}
        .super-winner {{ font-size: {super_winner_font}; font-weight: 800; color: #1e1b4b; margin-bottom: 2px; line-height: 1.15; }}
        .super-stat {{ font-size: {super_stat_font}; font-weight: 700; color: #4338ca; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 9px; margin-bottom: 11px; }}
        .metric-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 9px 11px; text-align: center; }}
        .metric-val {{ font-size: {metric_val_font}; font-weight: 800; color: #0f172a; margin-bottom: 2px; }}
        .metric-label {{ font-size: {metric_lbl_font}; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-sub {{ font-size: {metric_sub_font}; color: #3b82f6; margin-top: 2px; font-weight: 500; }}
        table {{ width: 100%; border-collapse: collapse; font-size: {table_font}; margin-bottom: 7px; }}
        th {{
            background: #f1f5f9; color: #334155; font-weight: 700; text-transform: uppercase;
            font-size: {th_font}; letter-spacing: 0.4px; padding: {th_pad}; border-top: 1px solid #cbd5e1; border-bottom: 2px solid #cbd5e1; text-align: left;
        }}
        td {{ padding: {td_pad}; border-bottom: 1px solid #f1f5f9; color: #1e293b; vertical-align: middle; }}
        tr:nth-child(even) td {{ background-color: #fafafa; }}
        .text-right {{ text-align: right; }}
        .text-center {{ text-align: center; }}
        .status-badge {{ display: inline-block; padding: {badge_pad}; border-radius: 10px; font-size: {badge_font}; font-weight: 700; }}
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
        table.full-table {{ font-size: 16px; }}
        table.full-table th {{
            font-size: 12px;
            padding: 4.5px 8px;
            letter-spacing: 0.5px;
        }}
        table.full-table td {{
            padding: 1.6px 8px;
            font-size: 16px;
            line-height: 1.15;
        }}
        table.full-table .progress-val {{
            font-size: 13.5px;
            line-height: 1.1;
        }}
        table.full-table .progress-bar-container {{
            width: 70px;
            height: 5px;
        }}
        table.full-table .status-badge {{
            font-size: 11.5px;
            padding: 2.5px 8px;
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
        .page-break {{ page-break-before: always; }}
        .footer {{ font-size: 8px; color: #94a3b8; text-align: center; margin-top: 6px; border-top: 1px solid #e2e8f0; padding-top: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            {logo_html}
            <div class="header-title">
                <h1>🏳️‍🌈 SWIFTEMBER 2026</h1>
                <p>Birmingham Swifts — {'Final Month-End Wrap-Up & Full Challenge Results' if week_num >= 5 else f'Week {week_num} Progress & Leaderboard Report'}</p>
            </div>
        </div>
    </div>

    <div class="section-title">{'⚡️ FINAL DAYS SWIFTEMBER HEROES' if week_num >= 5 else '⚡️ WEEKLY SWIFTEMBER HEROES'}</div>
    <div class="superlatives-grid">
        <div class="super-card">
            <div class="super-icon">🐣</div>
            <div class="super-award">Rising Swift</div>
            <div class="super-sub">Short Target (≤ {short_barrier:.0f} km)</div>
            <div class="super-winner">{rising_swift['registered_name'] if rising_swift else '-'}</div>
            <div class="super-stat">{f"{rising_swift['pct_weekly']:.1f}% Weekly Goal ({rising_swift['distance']:.1f} km)" if rising_swift else '-'}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🌟</div>
            <div class="super-award">Goal Setter</div>
            <div class="super-sub">Medium Target ({short_barrier+1:.0f}–{long_barrier:.0f} km)</div>
            <div class="super-winner">{pace_setter['registered_name'] if pace_setter else '-'}</div>
            <div class="super-stat">{f"{pace_setter['pct_weekly']:.1f}% Weekly Goal ({pace_setter['distance']:.1f} km)" if pace_setter else '-'}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🔥</div>
            <div class="super-award">Road Warrior</div>
            <div class="super-sub">Long Target (> {long_barrier:.0f} km)</div>
            <div class="super-winner">{road_warrior['registered_name'] if road_warrior else '-'}</div>
            <div class="super-stat">{f"{road_warrior['pct_weekly']:.1f}% Weekly Goal ({road_warrior['distance']:.1f} km)" if road_warrior else '-'}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">🏔</div>
            <div class="super-award">Mountain Goat</div>
            <div class="super-sub">Most Elevation</div>
            <div class="super-winner">{elev_runner['registered_name'] if elev_runner else '-'}</div>
            <div class="super-stat">{f"{elev_runner['elev']} Elevation" if elev_runner else '-'}</div>
        </div>
        <div class="super-card">
            <div class="super-icon">⚡️</div>
            <div class="super-award">Speed Demon</div>
            <div class="super-sub">Fastest Avg Pace</div>
            <div class="super-winner">{speed_runner['registered_name'] if speed_runner else '-'}</div>
            <div class="super-stat">{f"{speed_runner['pace']} ({speed_runner['distance']:.1f} km)" if speed_runner else '-'}</div>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-val">{total_pledge:,.0f} km</div>
            <div class="metric-label">Total Month Pledge</div>
            <div class="metric-sub">{len(matched_runners)} Registered Runners</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{total_cum_logged:,.1f} km</div>
            <div class="metric-label">{card_dist_label}</div>
            <div class="metric-sub">{card_dist_sub}</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{pct_pace_rate:.1f}%</div>
            <div class="metric-label">{'Challenge Target Progress' if week_num >= 5 else f'Week {week_num} Pace Progress'}</div>
            <div class="metric-sub">{total_cum_logged:,.1f} / {expected_cum_target:,.1f} km Target</div>
        </div>
        <div class="metric-card">
            <div class="metric-val">{len(mtd_active)} / {len(matched_runners)}</div>
            <div class="metric-label">{card_active_label}</div>
            <div class="metric-sub">{card_active_sub}</div>
        </div>
    </div>

    <div class="section-title">{'🏁 FINAL DAYS ACHIEVEMENT LEADERBOARD' if week_num >= 5 else '🎯 WEEKLY ACHIEVEMENT LEADERBOARD'}</div>
    <table class="weekly-table">
        <thead>
            <tr>
                <th class="text-center" style="width: 34px;">Rank</th>
                <th>Runner Name</th>
                <th class="text-right">{'Period Logged' if week_num >= 5 else 'Week Logged'}</th>
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

    <div class="section-title">{'🏆 FINAL SWIFTEMBER FULL REPORT' if week_num >= 5 else '📋 FULL SWIFTEMBER REPORT'}</div>
    <table class="full-table">
        <thead>
            <tr>
                <th class="text-center" style="width: 25px;">#</th>
                <th>Participant Name</th>
                <th class="text-right">Monthly Pledge</th>
                <th class="text-right">Total Logged (MTD)</th>
                <th class="text-right">Remaining</th>
                <th class="text-center">Monthly Progress</th>
                <th class="text-center">Challenge Status</th>
            </tr>
        </thead>
        <tbody>
            {roster_rows}
        </tbody>
    </table>

    <div class="footer">
        Swiftember 2026 Challenge Report • Birmingham Swifts Running Club
    </div>
</body>
</html>
"""
    return html

def main():
    parser = argparse.ArgumentParser(description="Generate Swiftember Weekly PDF & Markdown Report")
    parser.add_argument("-i", "--input", help="Path to raw Strava leaderboard data text file (or stdin if omitted)")
    parser.add_argument("-w", "--week", type=int, default=1, help="Week number (1, 2, 3, 4). Default: 1")
    parser.add_argument("-o", "--output-pdf", help="Output PDF file path (default: ~/Downloads/Swiftember_2026_Week{N}_Report.pdf)")
    parser.add_argument("-t", "--title-sub", default="Official Swiftember Report", help="Subtitle under badge in header")
    parser.add_argument("-f", "--font-size", choices=["large", "compact"], default="large", help="Font size preset: 'large' (default bigger fonts) or 'compact'")
    args = parser.parse_args()

    roster = load_roster()
    aliases = load_aliases()

    if args.input and os.path.exists(args.input):
        with open(args.input, "r", encoding="utf-8") as f:
            raw_data = f.read()
    else:
        # Check if weekly input file exists in data/
        week_input_file = os.path.join(DATA_DIR, f"week_{args.week}_strava.txt")
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

    historical_stats = load_historical_stats(up_to_week=args.week)
    strava_entries = parse_strava_table(raw_data)
    matched_runners = process_swiftember_data(strava_entries, roster, aliases, week_num=args.week, historical_stats=historical_stats)

    # Save current week stats to data/week_{args.week}_stats.json
    save_week_stats(args.week, matched_runners)

    # Generate HTML
    html_content = generate_html_report(matched_runners, week_num=args.week, badge_subtitle=args.title_sub, font_size=args.font_size)
    
    html_path = os.path.join(BASE_DIR, f"temp_report_week{args.week}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Output PDF
    downloads_dir = os.path.expanduser("~/Downloads")
    default_pdf_name = "Swiftember_2026_Final_Report.pdf" if args.week >= 5 else f"Swiftember_2026_Week{args.week}_Report.pdf"
    default_pdf_path = os.path.join(downloads_dir, default_pdf_name)
    pdf_path = args.output_pdf if args.output_pdf else default_pdf_path

    chrome_cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        f"file://{os.path.abspath(html_path)}"
    ]

    subprocess.run(chrome_cmd, check=True)
    if args.week >= 5:
        # Also copy to Week5 path for completeness
        w5_path = os.path.join(downloads_dir, "Swiftember_2026_Week5_Report.pdf")
        if pdf_path != w5_path:
            import shutil
            shutil.copyfile(pdf_path, w5_path)

    report_title = "Final Month-End Wrap-Up" if args.week >= 5 else f"Week {args.week}"
    print(f"\n[SUCCESS] Swiftember {report_title} Report successfully generated!")
    print(f"📄 PDF Output: {pdf_path}")
    if args.week >= 5:
        print(f"📄 Also saved as: {os.path.join(downloads_dir, 'Swiftember_2026_Week5_Report.pdf')}")
    weekly_active_count = len([m for m in matched_runners if m['distance'] > 0])
    mtd_active_count = len([m for m in matched_runners if m['cum_distance'] > 0])
    print(f"📊 Processed: {len(matched_runners)} registered runners ({weekly_active_count} active in {report_title}, {mtd_active_count} active MTD)")

if __name__ == "__main__":
    main()
