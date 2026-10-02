#!/usr/bin/env python3
"""
Generate detailed 5-week analysis and encouraging shoutouts for all 56 Swiftember goal achievers.
"""
import json
import os

SCRATCH_PATH = "/Users/bowang/.gemini/antigravity-ide/brain/5f747ba1-1978-4848-a3b6-12aec21cf04e/scratch/finishers_analysis.json"
SHOUTOUTS_PATH = os.path.join(os.path.dirname(__file__), "shoutouts.json")
ARTIFACT_PATH = "/Users/bowang/.gemini/antigravity-ide/brain/5f747ba1-1978-4848-a3b6-12aec21cf04e/swiftember_2026_finishers_shoutouts.md"

with open(SCRATCH_PATH, "r", encoding="utf-8") as f:
    finishers = json.load(f)

# Personalized shoutout messages mapping based on deep analysis of each runner's 5-week journey
custom_messages = {
    "Adrián Nieves": {
        "tag": "💥 Target Smasher & Seville 8k Ready",
        "analysis": "Rebuilding fitness after injury with immense discipline, peaking in Week 4 with 17.7 km and a strong 10.0 km in Week 5.",
        "message": "What an extraordinary comeback! You didn't just meet your 25 km target—you demolished it by over 206%, logging 51.7 km across 9 runs. From injury rehab to peak fitness for the Seville 8 km, your patience and dedication have been a masterclass in resilience!"
    },
    "Jon Williams": {
        "tag": "🌟 Steady Progression & 195% Smashed",
        "analysis": "Quadrupled mileage from Week 1 (5.0 km) to Week 2 (20.0 km) and kept crushing 16-22 km each week.",
        "message": "A phenomenal month of smart, progressive running! Bouncing back from injury, you quadrupled your mileage after Week 1 and never looked back, stacking 68.2 km on your 35 km goal. Consistent, measured, and unstoppable!"
    },
    "Anthony Morgan": {
        "tag": "🚀 Massive +60.8 km Surplus & 992m Elev",
        "analysis": "Blazed out of the gate with 43.5 km and 38.3 km in weeks 1-2, logging a half marathon long run.",
        "message": "Blistering pace and relentless climbing! You opened Swiftember with two massive 40 km weeks and conquered nearly 1,000 m of elevation, delivering 135.8 km on a 75 km target (+60.8 km surplus). Pure endurance brilliance!"
    },
    "Andrea Bohn": {
        "tag": "👟 Frequency Queen • 21 Runs Logged",
        "analysis": "Clocked in nearly every other day with 21 separate runs, maintaining unwavering regularity across all 5 weeks.",
        "message": "The absolute benchmark of running consistency! Lacing up 21 times across 5 weeks, you quietly transformed steady outings into 63.1 km—crushing your 35 km pledge by 180%. The habit of showing up every single week is inspirational!"
    },
    "David Purnell": {
        "tag": "🔥 +39.6 km Surplus & Week 4 Peak",
        "analysis": "Consistent 16-20 km weekly base followed by a brilliant 28.8 km surge in Week 4.",
        "message": "Superb pacing across the month! After laying down rock-solid weekly mileage in the first three weeks, you hit hyperdrive in Week 4 with nearly 29 km, crossing the line at 89.6 km (179% of goal). Incredible engine and focus!"
    },
    "Harvey Degan": {
        "tag": "⚡️ Week 1 Thunderclap & Half Marathon Hero",
        "analysis": "Stormed the challenge with a jaw-dropping 49.3 km in Week 1, including a 23.0 km long run.",
        "message": "Talk about making a statement! You effectively locked down your entire monthly pledge in Week 1 alone with a staggering 49.3 km week and a 23 km long run. Finishing on 85.5 km with 474 m elevation is top-tier determination!"
    },
    "Ross Newman": {
        "tag": "🏔 Steady Climber & 629m Elevation",
        "analysis": "Model of metronomic consistency: 24.0 km, 21.3 km, 20.4 km, and 18.7 km across the first four weeks.",
        "message": "Clockwork consistency at its finest! You delivered four consecutive 20 km+ weeks with remarkable composure and 629 m of hill climbing, cruising to 84.4 km on your 50 km pledge (169%). Smooth, dependable, and strong!"
    },
    "Jack Whitfield": {
        "tag": "🎯 Fortnight Finisher & Fast Target",
        "analysis": "Hit his 25 km target within the first fortnight with 14.3 km and 12.0 km, adding a 15.0 km surge in Week 4.",
        "message": "Speedy, clinical, and effective! You reached 100% of your pledge in the first fortnight, then capped it off with a 15 km Week 4 surge to finish on 41.3 km (165%). Outstanding execution from start to finish!"
    },
    "Richard Lakin": {
        "tag": "🗽 Berlin Major Conqueror & +52.1 km Surplus",
        "analysis": "Traded beer for marathon miles! 40.9 km (W1), 32.0 km (W2), 29.9 km (W3), peaking with a 49.3 km Berlin week.",
        "message": "Trading your beloved pints for marathon miles paid off in golden fashion! Four massive weeks peaked with a triumphant 42.6 km through the streets of Berlin, racking up 152.1 km (+52.1 km surplus). A true marathon legend!"
    },
    "Sam Gower": {
        "tag": "💪 Double-Century Seeker & 818m Elev",
        "analysis": "Unbeatable consistency: 21.9 km, 23.7 km, 23.7 km, and 27.9 km, topping 100 km total.",
        "message": "The epitome of discipline! Week after week, you banked 22 to 28 km like clockwork, taking on London Pride 10K, climbing 818 m, and breaking through the 100 km barrier (103.4 km). Fantastic grit and momentum!"
    },
    "Scott Brough": {
        "tag": "🚀 Pride 10K Hero & 144% Achieved",
        "analysis": "Alternated solid maintenance with huge breakthrough weeks (30.4 km W2, 32.6 km W4).",
        "message": "What an energetic, spirited month! From showing up in force at London Pride 10K to launching huge 30 km+ surges in Weeks 2 and 4, you effortlessly shattered your 75 km target to reach 107.8 km. Outstanding dedication!"
    },
    "Mark Blakeman": {
        "tag": "⭐ 3rd Major Star Hunter & +65.0 km Surplus",
        "analysis": "Averaged 50+ km every week (54.0, 53.1, 42.9, 59.3), completed Berlin Marathon in 42.7 km.",
        "message": "A breathtaking masterclass in marathon endurance! With four consecutive 50 km+ weeks, 1,166 m of climbing, and a stellar Berlin Marathon, you earned your 3rd Major star and banked 215.0 km. Chasing that Boston BQ with true champion spirit!"
    },
    "Thomas Glave": {
        "tag": "👑 The Distance King • 282.1 km Logged",
        "analysis": "Monster weeks: 74.5 km (W1), 90.0 km (W2), 86.8 km (W4), and 30.8 km (W5). Marathon long run of 42.6 km.",
        "message": "Hail the Distance King of Swiftember! Logging 282.1 km across 24 runs and conquering 1,343 m of climbing, you set the standard for high-mileage mastery. An awe-inspiring achievement that pushed the entire club forward!"
    },
    "Joe Pinder": {
        "tag": "🧘 Calm, Composed & Berlin Finisher",
        "analysis": "Triple 50 km+ weeks (52.6, 51.5, 58.9 km) culminating in a 42.6 km Berlin Marathon.",
        "message": "Cool, calm, and effortlessly powerful! You quietly laid down three 50 km+ weeks, conquered 1,324 m of elevation, and crossed the Berlin finish line with poise to bank 208.2 km (+58.2 km surplus). A truly majestic campaign!"
    },
    "Jimmy Simpson": {
        "tag": "⚡️ 16 Runs of Pure Energy & 99.8 km",
        "analysis": "Consistent 20-24 km every single week, with a strong 16.2 km Week 5 wrap-up.",
        "message": "Rock-steady rhythm week in and week out! Logging 16 runs with unmatched dependability, you built up week after week to land at 99.8 km—133% of your 75 km goal. A fantastic testament to steady, regular training!"
    },
    "James Chaundy": {
        "tag": "🏃 Half Marathon Ace & 133% Smashed",
        "analysis": "Kicked off with a huge 36.4 km Week 1, backed it up with 23-28 km in W3 and W4, including a 21.3 km half marathon.",
        "message": "A powerhouse opening week and brilliant long-distance execution! Your 21.3 km half marathon and consistent high-mileage weeks brought you to 99.8 km (133% of goal) with 759 m of climbing. Fantastic running!"
    },
    "Bradley M 🏳️‍🌈💪🏃‍♂️": {
        "tag": "💪 Week 3 & 4 Power Surges",
        "analysis": "Doubled down with back-to-back 10.0 km and 10.1 km weeks in the second half of September.",
        "message": "A brilliant mid-challenge surge! You ramped up your mileage right when it mattered, putting in back-to-back 10 km weeks to smash your 20 km pledge with 26.1 km (130.5%). That rainbow power and determination shone through!"
    },
    "Michael Lakin": {
        "tag": "🔥 Pure Grit & Berlin Marathon Finish",
        "analysis": "Two 32.1 km weeks followed by a 42.7 km Berlin Marathon effort, achieving 127.6% of goal.",
        "message": "When the going gets tough, you simply push harder! Backing up two 32 km opening weeks with an inspiring 42.7 km finish through the Brandenburg Gate, you proved your indomitable spirit and racked up 127.6 km. Magnificent effort!"
    },
    "Lex Hooper": {
        "tag": "🚀 Mid-Month Surge & 126% Achieved",
        "analysis": "Huge leap from 6.7 km in W1 to 18.1 km in W2 and 18.9 km in W4.",
        "message": "What an awesome progression! You launched massive 18 km+ weeks in Weeks 2 and 4, turning a 40 km pledge into a 50.3 km triumph. Smart pacing, great endurance, and a fantastic goal-smashing finish!"
    },
    "John Simpson": {
        "tag": "⚡️ 5:11 /km Pacing & 123 km Logged",
        "analysis": "Exploded in Week 2 with 39.8 km, maintaining 26-32 km through the second half with 15 km long runs.",
        "message": "Speed and stamina in perfect harmony! After an explosive 39.8 km Week 2, you kept the throttle pinned at a rapid 5:11 /km average pace, logging 123.0 km across 14 runs with 789 m of climbing. Pure class!"
    },
    "Jack Dean": {
        "tag": "🏃‍♂️ Chicago Marathon Bound • 244.0 km",
        "analysis": "Stacked monster weeks (68.9, 74.3, 54.4 km), 22 runs, 1,908 m elevation, and 5:09 /km avg pace.",
        "message": "A monumental training block! Training for the Chicago Marathon, you conquered 244.0 km across 22 runs with nearly 2,000 m of climbing and a sizzling 5:09 /km pace. Chicago is going to feel your power—what a run of form!"
    },
    "Ian Bush": {
        "tag": "💪 Ankle Rehab Victory & 119% Smashed",
        "analysis": "Overcame ankle injury with structured progression, culminating in a 24.9 km Week 4.",
        "message": "A truly inspiring comeback story! Managing an ankle injury with immense care and patience, you steadily rebuilt confidence and peaked with a 25 km Week 4 to hit 60.7 km on your 51 km target. A triumphant return to form!"
    },
    "Patrick Ryan": {
        "tag": "🏔 548m Climbing & 5:34 /km Speed",
        "analysis": "Burst through the target with 21.1 km in Week 2 and balanced double-digit weeks throughout.",
        "message": "Smooth, rhythmic, and purposeful running! You paired swift 5:34 /km pacing with 548 m of elevation gain to cruise past your 50 km goal to 58.6 km. Great form, great momentum, and a thoroughly deserved finish!"
    },
    "Gabriel Stirling": {
        "tag": "⚡️ 5:09 /km Speed Demon & 20 Runs",
        "analysis": "High frequency (20 runs), consistent 23-32 km weekly miles, and blazing speed.",
        "message": "Lightning fast and ultra-consistent! Lacing up 20 times across the challenge, you held a blistering 5:09 /km pace across 117.1 km, making the Top 5 Speed leaderboard. Speed, endurance, and consistency all in one!"
    },
    "Alexander Brown": {
        "tag": "💪 Comeback King & Berlin Marathoner",
        "analysis": "Consistent 50 km+ weeks (58.0, 57.6, 48.3, 63.6 km), 1,354 m elev, 42.6 km marathon.",
        "message": "Overcoming tough obstacles in training, you picked yourself up and built an absolute fortress of mileage—peaking with a 63.6 km week and conquering the Berlin Marathon. 233.2 km logged with immense heart and courage!"
    },
    "Richard Wilkes": {
        "tag": "🥐 Pastry-Fueled Berlin Conqueror",
        "analysis": "Solid 38.0, 25.9, 32.3 km buildup followed by a 47.7 km Berlin Marathon week.",
        "message": "Proof that pastries and marathon miles make the ultimate winning combination! You powered through four demanding weeks and crossed the Berlin finish line in style, logging 143.9 km with 685 m of climbing. Pure joy and dedication!"
    },
    "Bo Wang": {
        "tag": "⭐ 3rd Major Star & 86.1 km Week 1 Blast",
        "analysis": "Blasted off with an 86.1 km opening week, 20 runs, 5:11 /km pace, and completed Berlin Marathon.",
        "message": "From an 86 km Week 1 thunderclap to securing your 3rd World Marathon Major star in Berlin, you logged 228.3 km with incredible determination and 5:11 /km pace. A fantastic milestone on your Major journey!"
    },
    "Pete Hall": {
        "tag": "🌟 Race Debut at Pride 10K & 85.4 km",
        "analysis": "Built steadily from 16.9 km to a 25.2 km Week 4 peak, tackling his first official race.",
        "message": "What an unforgettable month for your running journey! You completed your first official race at London Pride 10K, tackled a bold 75 km pledge, and surged past it to 85.4 km with 11 solid runs. The sky is the limit!"
    },
    "Helen Williams": {
        "tag": "🇫🇷 Paris & Berlin Double 🇩🇪 Marathoner",
        "analysis": "Second marathon of 2026! 43.7 km (W1), 28.1 km (W2), 48.7 km (W4 Berlin Marathon).",
        "message": "Two full marathons in a single year—what an awe-inspiring achievement! Conquering Berlin on top of Paris earlier this year, you banked 141.5 km and 874 m of climbing, easily beating your 125 km pledge. True club royalty!"
    },
    "Chris Bloxham": {
        "tag": "🎯 Fortnight Target Hit & 39.3 km",
        "analysis": "Banked 18.2 km in Week 2 with near-10 km efforts, comfortably hitting his 35 km goal.",
        "message": "Target locked and loaded early! With focused outings and a strong 18.2 km Week 2, you smoothly navigated past your 35 km target to 39.3 km. Efficient, well-managed, and right on the money!"
    },
    "Farrell Baker": {
        "tag": "⚡️ 5:15 /km Pace & Consistent Weekly Mileage",
        "analysis": "15 runs, 23.6, 29.7, 22.6, 16.4, 16.7 km across all 5 weeks.",
        "message": "The definition of rhythm! You showed up every single week with 16 to 30 km, maintaining a crisp 5:15 /km pace across 15 runs and topping 109 km. A flawless, beautifully paced Swiftember campaign!"
    },
    "Ian Allen 🏳️‍🌈": {
        "tag": "🏃 Race Machine & 1,754m Mountain Climber",
        "analysis": "21 runs, 61.8 km W1, 59.0 km W4, Berlin Marathon finish, 1,754 m climbing.",
        "message": "A running powerhouse who never slows down! Lacing up for 21 runs, you racked up 217.6 km, conquered Berlin, and scaled 1,754 m of elevation—all while bringing incredible vibrancy to the club. Unmatched passion and energy!"
    },
    "Dean Haycock": {
        "tag": "📈 Master of Progression: 0 to 14.2 km Peak",
        "analysis": "Progressed from 5 km in W2 to 8 km in W3 and a 14.2 km peak in W4.",
        "message": "A textbook progression curve! You stepped up your distance each week, capping it off with a 14.2 km surge in Week 4 to surpass your 25 km target. Great confidence, smart ramp-up, and a well-earned celebration!"
    },
    "Chris W": {
        "tag": "🔥 The Streak Master & 14.3 km Long Run",
        "analysis": "Maintained his streak while logging 17.3 km (W1), 14.3 km (W3), and 22.0 km (W4).",
        "message": "Keeping the streak alive and blazing! You paired your daily consistency with strong weekend long runs, hitting 22 km in Week 4 to comfortably surpass your 50 km goal (53.6 km). Streak on, legend!"
    },
    "Sam Lewis": {
        "tag": "🎯 Metronomic Consistency (21k / 21k / 20k)",
        "analysis": "Three consecutive ~21 km weeks across W1-W3, finishing on 80.0 km.",
        "message": "Unshakeable pacing discipline! You laid down 21.9 km, 21.2 km, and 20.6 km across the opening three weeks, hitting your 75 km target with time to spare (80.0 km). Calm, steady, and thoroughly effective!"
    },
    "Benjamin Lane": {
        "tag": "⚡️ 4:58 /km Sub-5 Pacing & Pride 10K Champion",
        "analysis": "1st Swift in London Pride 10K, Week 3 Speed Demon, 40.1 km Week 2 surge, 21.6 km long run.",
        "message": "Pure speed! Leading the Swifts at London Pride 10K and holding an average pace of 4:58 /km across 106.5 km, you showed supreme class. A half marathon long run and a 40 km peak week made this an unforgettable campaign!"
    },
    "James S": {
        "tag": "👟 12 Runs of Regularity & 5:20 /km Speed",
        "analysis": "Four consecutive ~18-20 km weeks, finishing on 79.8 km on a 75 km goal.",
        "message": "Reliable, swift, and composed! Averaging 5:20 /km across 12 well-paced runs, you kept the weekly totals between 15 and 21 km to cross your 75 km goal with ease. A wonderfully balanced Swiftember!"
    },
    "Matthew Rushton": {
        "tag": "🚀 Berlin Marathon Debut & 159.2 km Total",
        "analysis": "58.6 km Week 1, caught up rapidly during training, conquered Berlin in 42.7 km.",
        "message": "What an entrance onto the marathon stage! A massive 58.6 km Week 1 gave you the runway to conquer the Berlin Marathon and bag 159.2 km total. You rose to the challenge brilliantly and ran with supreme pride!"
    },
    "Alice Wilkinson": {
        "tag": "🦅 Endurance Titan • 83.0 km Ultra Conqueror",
        "analysis": "Conquered a 50-mile Ultra Marathon in Week 2, logging 83.0 km in a single run.",
        "message": "Our Endurance Titan! Conquering an 83 km 50-mile Ultra Marathon on September 12th was one of the defining moments of Swiftember 2026. Banking 132.6 km total to beat your 125 km pledge, your mental grit and physical endurance are heroic!"
    },
    "Christopher Bainbridge": {
        "tag": "👑 Top Swiftember Berliner • 264.7 km",
        "analysis": "25 runs, 75.3 km W1, 61+ km every week, 1,231 m elevation, completed Berlin Marathon.",
        "message": "The tireless workhorse! Battling through training setbacks, you bounced back to log 264.7 km across 25 runs—the highest total among all Berlin runners. Four relentless 60-75 km weeks and a glorious marathon finish. Take a bow!"
    },
    "Tim Reeves": {
        "tag": "🌟 Marathon Debutant & +1,033m Elevation",
        "analysis": "First full marathon! 47.1 km W1, 37.0 km W2, 47.9 km W4, 158.0 km total on 150 km target.",
        "message": "Tackling your very first full marathon with 158 km banked and over 1,000 m of climbing! You poured enormous heart and sweat into this training block, and your 42.8 km Berlin finish is an achievement you'll cherish forever!"
    },
    "Barry Cassidy": {
        "tag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Glasgow Half Marathon Ready & 5:12 /km",
        "analysis": "Bounced back from injury with 29.6 km, 37.0 km, and a 26.1 km Week 5 with 21.1 km half marathon.",
        "message": "A masterful recovery and sharpening phase! Managing your return from injury with supreme discipline, you signed off Week 5 with a blistering 21.1 km half marathon effort to hit 104.7 km at 5:12 /km pace. Ready to fly in Glasgow!"
    },
    "Adam Bown": {
        "tag": "⚡️ Speed Demon Winner • 4:45 /km & 208.1 km",
        "analysis": "Fastest weighted average pace in the club (4:45 /km) over 208 km with 1,727 m elevation.",
        "message": "Swift by name, swift by nature! Clocking 208.1 km across 21 runs while averaging an astonishing 4:45 /km pace and scaling 1,727 m of hills, you claimed the official Speed Demon crown. Absolutely electric running from start to finish!"
    },
    "Daniel Bridge": {
        "tag": "🚀 Week 3 Surge & Pride 10K Supporter",
        "analysis": "Stepped up from 20 km in W1 to a 32.4 km peak in W3, finishing on 67.5 km.",
        "message": "Great tenacity and tactical pacing! Your 32.4 km peak in Week 3 did the heavy lifting, taking you past your 65 km target with 67.5 km total and 393 m of climbing. A fantastic month of running and club spirit!"
    },
    "James Horne": {
        "tag": "⚡️ 5:15 /km Precision & 100% Target Hit",
        "analysis": "Hit 8.7 km, 6.2 km, and 10.0 km across 3 targeted runs to reach 24.9 km on 24 km goal.",
        "message": "Precision engineering! You targeted 24 km and delivered 24.9 km at a rapid 5:15 /km average pace, completing exactly what you set out to achieve with no fuss and total focus. Spot on!"
    },
    "Matt Mackinnon-Coleman": {
        "tag": "🏔 874m Elevation & 102.4 km Century",
        "analysis": "Consistent 24-30 km weeks in W2-W4, 13 runs, 5:25 /km average pace.",
        "message": "A century of kilometers backed by serious hill power! Clocking 102.4 km across 13 runs with 874 m of elevation gain and a swift 5:25 /km pace, you made joining the Century Club look easy. Tremendous effort!"
    },
    "Jake Colbourn": {
        "tag": "🏔 Mountain Goat & Frequency Champion (27 Runs)",
        "analysis": "Most runs in the club (27), 81.9 km Ultra, 3,074 m elevation (club record), 204.4 km total.",
        "message": "Our undisputed Mountain Goat and run frequency champion! Logging 27 runs, conquering an 81.9 km 50-mile Ultra, and climbing a staggering 3,074 m of elevation, your endurance and resilience this month were nothing short of superhuman!"
    },
    "Lee Singleton": {
        "tag": "💪 Inspiring Comeback & 102.0 km Century",
        "analysis": "Overcame seizure recovery, ran London Pride 10K, balanced 22-27 km weekly to hit 102.0 km.",
        "message": "One of the most inspiring achievements of Swiftember! Pushing through recovery from last year's seizure, you laced up 13 times, conquered London Pride 10K, and crested the 100 km mountain with 102.0 km and 863 m of elevation. True Swifts courage!"
    },
    "Laura Rafailov": {
        "tag": "🌸 Century Finisher & London Pride 10K",
        "analysis": "Consistent four weeks of 20-30 km, finishing strong with 12.0 km in W5 to break 100 km.",
        "message": "Century conquered in style! From joining the Pride 10K squad to steadily banking 20 to 30 km each week, you crossed the finish line at 101.8 km with 666 m of climbing. Fantastic focus and wonderful club spirit!"
    },
    "Neesa": {
        "tag": "💪 Gym S&C Powerhouse & 38 km Mega-Run",
        "analysis": "Combined gym S&C with an incredible 38.0 km long run in Week 2 to lock in 50.9 km.",
        "message": "Strength and power in action! Balancing heavy gym strength and conditioning work, you unleashed a monumental 38.0 km run in Week 2, locking in your 50 km target before mid-month. That strength training paid immense dividends!"
    },
    "Tom dawson": {
        "tag": "⚡️ Back-to-Back 20k+ Weeks & 45.6 km Total",
        "analysis": "Delivered 24.1 km in W2 and 21.5 km in W3 to hit 101.3% of his 45 km pledge.",
        "message": "Two decisive, high-impact weeks! You delivered back-to-back 20 km+ weeks in Weeks 2 and 3, effortlessly hitting 45.6 km to secure your Swiftember goal. Efficient, composed, and job done!"
    },
    "Phil Deeley": {
        "tag": "👟 14 Runs of Dedication & 69.7 km Total",
        "analysis": "Consistent opening fortnight (25.9 km, 23.8 km) backed by 14 runs across the month.",
        "message": "Fourteen runs of pure commitment! You laid down two strong 25 km weeks early on, maintaining focus throughout the month to reach 69.7 km on your 69 km pledge with 408 m of climbing. Superb dedication!"
    },
    "James Evans": {
        "tag": "🎯 Clutch Week 4 Double & 101% Goal Hit",
        "analysis": "Two focused 5 km runs in Week 4 to hit 10.1 km on 10 km pledge.",
        "message": "Clutch performance under pressure! When Week 4 arrived, you stepped up with two crisp 5 km runs, hitting 10.1 km and sealing your 100% completion badge with precision. Fantastic execution!"
    },
    "Joshua Burnett": {
        "tag": "🏃 Marathon+ Hero (43.1 km) & 95.9 km Century",
        "analysis": "Unleashed a massive 53.5 km Week 2 including a 43.1 km marathon-plus distance long run.",
        "message": "A breathtaking marathon effort! In Week 2 you unleashed an epic 43.1 km long run as part of a 53.5 km week, ultimately logging 95.9 km on your 95 km target. That long-run grit was unforgettable!"
    },
    "Joshua Savage": {
        "tag": "👑 Club Chair Grit & Berlin Marathoner",
        "analysis": "18 runs, 201.4 km logged, 2,759 m elevation, conquered Berlin Marathon.",
        "message": "Leading from the front! You might complain in the club chat, but on the roads you delivered 201.4 km, scaled an enormous 2,759 m of elevation, and conquered the Berlin Marathon with true grit. A proud achievement for our club chair!"
    },
    "Josh Heer": {
        "tag": "🎯 The Perfect 10 km Bullseye (100.0%)",
        "analysis": "Executed a flawless 10.0 km run to hit exactly 100.0% of his pledge.",
        "message": "The ultimate bullseye! You promised 10.0 km and delivered exactly 10.0 km on the dot at 6:36 /km pace. No wasted motion, no fuss—pure, perfect completion. Welcome to the Finisher Roll of Honor!"
    }
}

# Update shoutouts.json
with open(SHOUTOUTS_PATH, "r", encoding="utf-8") as f:
    shoutouts_data = json.load(f)

final_finishers_list = []
for f in finishers:
    name = f["name"]
    custom = custom_messages.get(name, {})
    final_finishers_list.append({
        "rank": f["rank"],
        "name": name,
        "target_km": f["target"],
        "total_km": f["total"],
        "pct_achieved": f["pct"],
        "surplus_km": f["surplus"],
        "total_runs": f["runs"],
        "total_elev_m": f["elev"],
        "avg_pace": f["pace"],
        "longest_run_km": f["longest"],
        "weekly_km": [w["dist"] for w in f["weeks"]],
        "tag": custom.get("tag", "🎉 Swiftember Goal Achiever"),
        "analysis": custom.get("analysis", ""),
        "shoutout": custom.get("message", f"Congratulations on completing {f['total']:.1f} km and smashing your {f['target']:.0f} km goal!")
    })

shoutouts_data["final_finishers"] = final_finishers_list
with open(SHOUTOUTS_PATH, "w", encoding="utf-8") as f:
    json.dump(shoutouts_data, f, indent=2)

print(f"Updated {SHOUTOUTS_PATH} with {len(final_finishers_list)} finisher shoutouts.")

# Build Markdown Artifact Document
md_lines = [
    "# 🏳️‍🌈 Swiftember 2026 • Finisher Roll of Honor & Individual Shoutouts",
    "",
    "> **Celebrating all 56 Birmingham Swifts runners who achieved and smashed their personal Swiftember targets!**",
    "> Out of 66 registered runners, **56 runners (84.8%)** achieved their goals, combining for **6,579.4 km** (115.3% of the 5,704 km club pledge), **706 runs**, and **41,917 m** of elevation gain.",
    "",
    "---",
    "",
    "## 🏆 Thematic Cohort Summaries",
    "",
    "1. **👑 The Double-Century Titans (200km+ Club)**: 11 runners who logged over 200 km each, led by Distance King **Thomas Glave** (282.1 km).",
    "2. **💥 The Target Smashers (140% - 207% of Goal)**: 11 runners who obliterated their pledges, led by Target Smasher **Adrián Nieves** (206.8%).",
    "3. **🏅 The Century Centurions (100km - 160km Milestone Legends)**: 17 runners who conquered marathon distance builds, Berlin Marathon, and major endurance milestones.",
    "4. **👟 The Consistency & Tactical Masters**: 17 runners who demonstrated precision execution, injury recovery triumphs, and clutch finishes.",
    "",
    "---",
    "",
    "## 📜 Comprehensive Individual Shoutouts & 5-Week Analysis (All 56 Finishers)",
    ""
]

for entry in final_finishers_list:
    w_trend = " → ".join([f"W{i+1}: {k:.1f}k" for i, k in enumerate(entry["weekly_km"])])
    elev_str = f"{entry['total_elev_m']:,} m" if entry['total_elev_m'] > 0 else "--"
    md_lines.append(f"### {entry['rank']}. {entry['name']}")
    md_lines.append(f"**Badge / Tag**: `{entry['tag']}`  ")
    md_lines.append(f"- **Challenge Target**: {entry['target_km']:.0f} km | **Total Logged**: **{entry['total_km']:.1f} km** ({entry['pct_achieved']:.1f}% • **+{entry['surplus_km']:.1f} km surplus**)")
    md_lines.append(f"- **Key Stats**: {entry['total_runs']} runs | Avg Pace: `{entry['avg_pace']}` | Elevation: {elev_str} | Longest Run: {entry['longest_run_km']:.1f} km")
    md_lines.append(f"- **5-Week Mileage Trend**: `{w_trend}`")
    md_lines.append(f"- **5-Week Journey Analysis**: *{entry['analysis']}*")
    md_lines.append(f"- 📣 **Personal Shoutout**: {entry['shoutout']}")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")

with open(ARTIFACT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"Generated Markdown artifact at {ARTIFACT_PATH}")
