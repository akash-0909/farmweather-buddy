# Submission Pack — FarmWeather Buddy

Fill in team names. Re-check every item against the Launchpad Timeline, Rules and Submission tabs.

## Project name
FarmWeather Buddy

## Problem statement (paste-ready)
Smallholder farmers make time-critical decisions, such as when to harvest or dry paddy, using raw weather numbers or generic forecasts that are hard to interpret for their own crop. A missed heavy-rain warning during harvest can cause grain loss, yet most weather apps do not say what the forecast means for a specific crop stage. Farmers need a clear, trustworthy, local explanation in their own language.

## Solution description (paste-ready)
FarmWeather Buddy lets a user choose a location and crop. It retrieves a live forecast from Open-Meteo, applies a transparent rain-risk rule based on IMD rainfall categories, and then uses a generative AI model to explain the result in plain English or Hindi with one cautious suggestion. Accuracy safeguards: the AI sees only the computed facts, any answer containing numbers not found in the forecast is rejected, and a rule-based explanation is shown if the AI is unavailable. The app always shows the data source and retrieval time, and states clearly when data is missing instead of guessing.

## Links to fill
- Live prototype: ______ (Streamlit Community Cloud URL)
- Demo video: ______ (use the length the Launchpad form asks for: 5 min per the form screenshot, 2–3 min per the pasted brief; confirm if unsure)
- GitHub repo (public): ______
- Deck: ______

## Deck outline (5–7 slides)
1. **Title and team** — name, tagline, members and roles
2. **Problem** — harvest-time rain losses, why generic forecasts don't help, who is affected
3. **Solution and features** — place + crop → live forecast → risk level → plain-language advice (English/Hindi) → source and time shown
4. **Architecture and innovation** — pipeline diagram; rule-based risk (auditable) + LLM explanation; number-grounding guard; graceful fallback
5. **Resilience and accuracy** — failure table from the README (API down, missing data, AI failure)
6. **Roadmap** — more crops and hazards (heat, frost), soil and market data only once real sources are integrated, SMS/WhatsApp delivery, more languages
7. **Live demo summary** — what the judges will see and the real-data proof

## Demo script (≈3 min; stretch to 5 with the architecture walkthrough)
1. (15 s) Problem in one sentence.
2. (30 s) Open the **live URL**. Search a place, select it, click Check forecast.
3. (45 s) Walk through risk banner, rain chart, table. Point at the source link and retrieval time.
4. (45 s) Show the AI advice; switch to Hindi. Say which parts are rules and which are AI.
5. (30 s) Show resilience: search a nonsense place (warning), then explain that with no key or API failure the app falls back to rules.
6. (30 s) Open the repo: `weather.py`, `risk.py`, `advisor.py`, `tests/`. Mention 9 passing tests.
7. (15 s) Roadmap and close.

Record the screen of the **real deployed app**. Do not show a mockup or a prerecorded flow as the product.

## Likely judge questions
- *How do you avoid hallucinations?* Facts computed in code, LLM restricted to them, numbers verified, fallback text.
- *What's beyond a chatbot?* Live data pipeline, deterministic risk logic, guardrail, failure handling, tests.
- *Why these thresholds?* IMD rainfall categories; configurable in `risk.py`.
- *What isn't covered?* One crop, one hazard, forecast only. Honest scope.
- *Can it scale?* Add crops as config entries; cache forecasts per location; swap the LLM provider in one function.

## Schedule (from Sat 31 Oct, ~01:30 IST to deadline Sun 1 Nov, 23:59 IST)

| When (IST) | Goal |
|---|---|
| Sat 01:30–02:30 | Run the app locally, confirm **live data works**, push to GitHub (public) |
| Sat 02:30–10:00 | **Sleep** |
| Sat 10:00–12:00 | Deploy to Streamlit Cloud, add secret, test the public URL on a phone |
| Sat 12:00–16:00 | Pick your demo location, test 5–6 places, fix bugs, tune the prompt (test Hindi) |
| Sat 16:00–19:00 | One real improvement: e.g. add a second hazard (heat/frost) or a 7-day outlook view |
| Sat 19:00–21:00 | Review the code with your teammate(s); everyone must be able to explain it |
| Sat 21:00–Sun 08:00 | Rest. Do not code late at night |
| Sun 08:00–11:00 | Deck (5–7 slides) and architecture slide |
| Sun 11:00–14:00 | Record the demo video from the live app; re-record if it stumbles |
| Sun 14:00–17:00 | Fill the submission form completely; verify links open in a private window |
| Sun 17:00–18:00 | **Submit.** Target 6 hours before the deadline |
| Sun 18:00–23:59 | Buffer only. Fix a broken link, nothing more |

## Final checklist
- [ ] Live URL opens without login; works for a few different places
- [ ] Repo is public with README, requirements, tests
- [ ] No API key committed (use secrets)
- [ ] Demo video link opens in a private window
- [ ] Deck has all 5 required sections
- [ ] Every teammate can explain architecture, data flow and AI logic
- [ ] Rules read: core logic built during the event; no mock or hardcoded data
