"""Allround Practice Case Generator — Streamlit web interface for v18.

Keep allround_practice_case_generator_v18_EN.py in the same directory.
The v18 calculation and selection functions remain the source of truth.
"""
from __future__ import annotations

import copy
import json
import random
import secrets
import tempfile
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

import allround_practice_case_generator_v18_EN as gen

st.set_page_config(
    page_title="Allround Practice Case Generator",
    page_icon="⛸️",
    layout="wide",
)

TIE_LABELS = {
    "No forced tie": "none",
    "Tie in classification after three distances": "classification",
    "Tie in the longest completed distance": "longest_distance",
    "Ties in both rankings": "both",
    "Tie around the qualification cut-off": "qualification_boundary",
}


def generate_case(config: gen.TournamentConfig) -> dict:
    """Use the generation workflow from the v18 main(), without console input.

    Do not silently accept cases that lack the required selection challenge.
    """
    rng = random.Random(config.seed)
    skaters = None
    incident_messages: list[str] = []
    tie_messages: list[str] = []
    pending_fourth_incidents: list[gen.RaceStatus] = []

    for _ in range(150):
        candidate = gen.create_initial_skaters_with_selection_challenge(config, rng)
        candidate_incidents: list[str] = []
        candidate_pending: list[gen.RaceStatus] = []

        if config.simulate_incidents:
            candidate_incidents, candidate_pending = gen.simulate_incidents(
                candidate, config.distances, config.incident_count, rng
            )
        gen.recalculate_all(candidate, config.distances)
        candidate_ties = gen.apply_tie_scenario(candidate, config, rng)
        gen.recalculate_all(candidate, config.distances)

        challenge_ok = gen.has_meaningful_fourth_distance_selection(
            candidate,
            config.qualification_limit,
            config.overall_rank_limit if config.apply_overall_rank_limit else None,
        )
        trap_ok = True
        if config.apply_overall_rank_limit and config.force_outside_top_x_longest_top_y:
            trap_ok = gen.has_outside_top_x_longest_top_y_trap(
                candidate, config.overall_rank_limit, config.qualification_limit
            )

        if challenge_ok and trap_ok:
            skaters = candidate
            incident_messages = candidate_incidents
            pending_fourth_incidents = candidate_pending
            tie_messages = candidate_ties
            break

    if skaters is None:
        raise RuntimeError(
            "No valid case could be generated with these constraints. "
            "Try another case number, fewer incidents, or less restrictive options."
        )

    selected, reserves = gen.select_for_fourth_distance(
        skaters,
        config.qualification_limit,
        config.reserve_count,
        config.overall_rank_limit if config.apply_overall_rank_limit else None,
    )
    incident_messages.extend(
        gen.apply_fourth_distance_incidents(
            selected, config.distances, pending_fourth_incidents, rng
        )
    )
    gen.recalculate_all(skaters, config.distances)

    return {
        "config": config,
        "skaters": skaters,
        "selected": selected,
        "reserves": reserves,
        "incident_messages": incident_messages,
        "tie_messages": tie_messages,
        "edited": False,
    }


def english_exercises(config: gen.TournamentConfig, case: dict) -> list[str]:
    """Clear English questions for the student and instructor exports."""
    longest = max(config.distances[:3])
    questions = [
        "Verify the classification after two distances, including ranks and total points.",
        "Determine the pairing and starting order for the third distance.",
        "Verify the classification after three distances, including ties and unclassified skaters.",
        f"Select {config.qualification_limit} skaters for the fourth distance, considering "
        f"both the overall classification and the {longest} m result.",
        f"Prepare an ordered reserve list of {config.reserve_count} skaters and explain your choices.",
        "Prepare the start list for the fourth distance. Explain the pairings and starting order.",
    ]
    if case["tie_messages"]:
        questions.append("Explain how each relevant tie affects the ranking and selection.")
    if case["incident_messages"]:
        questions.append("For each incident, assess its consequences for eligibility and selection.")
    questions.append("Which checks must the referee make before signing the start list?")
    return questions


def recalculate_selection(case: dict) -> None:
    config = case["config"]
    gen.recalculate_all(case["skaters"], config.distances)
    case["selected"], case["reserves"] = gen.select_for_fourth_distance(
        case["skaters"],
        config.qualification_limit,
        config.reserve_count,
        config.overall_rank_limit if config.apply_overall_rank_limit else None,
    )


def distance_table(case: dict, distance: int) -> pd.DataFrame:
    rows = []
    for s in case["skaters"]:
        status = s.statuses[distance]
        rows.append({
            "Rank": s.distance_ranks.get(distance),
            "Bib": s.bib,
            "Skater": s.name,
            "Time / status": gen.format_time(s.times[distance]) if status == "OK" else ("-" if status == "N/A" else status),
            "Points": f"{s.points[distance]:.3f}" if s.points[distance] is not None else "-",
        })
    return pd.DataFrame(rows).sort_values(
        ["Rank", "Bib"], na_position="last", kind="stable"
    ).reset_index(drop=True)


def classification_table(case: dict, count: int) -> pd.DataFrame:
    rows = []
    for s in sorted(case["skaters"], key=lambda x: gen.classification_sort_key(x, count)):
        rank = s.overall_rank_after_2 if count == 2 else s.overall_rank_after_3
        total = s.total_points_after_2 if count == 2 else s.total_points_after_3
        row = {"Rank": rank, "Bib": s.bib, "Skater": s.name}
        for distance in case["config"].distances[:count]:
            row[f"{distance} m"] = gen.format_time_with_rank(s, distance)
        row["Total points"] = f"{total:.3f}" if total is not None else "-"
        rows.append(row)
    return pd.DataFrame(rows)


def selection_table(skaters: list[gen.Skater]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "No.": i,
            "Bib": s.bib,
            "Skater": s.name,
            "Classification rank": s.overall_rank_after_3,
            "Longest-distance rank": s.longest_distance_rank,
        }
        for i, s in enumerate(skaters, 1)
    ])


def practice_csv(case: dict) -> bytes:
    config = case["config"]
    rows = []
    for distance in config.distances[:3]:
        for s in case["skaters"]:
            rows.append({
                "distance_m": distance,
                "bib": s.bib,
                "name": s.name,
                "status": s.statuses[distance],
                "time_s": s.times[distance] if s.statuses[distance] == "OK" else "",
            })
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def practice_text(case: dict) -> bytes:
    config = case["config"]
    lines = [
        "ALLROUND PRACTICE CASE — STUDENT WORKSHEET",
        "=" * 65,
        f"Category: {config.gender.title()}",
        f"Distances: {' / '.join(map(str, config.distances))} m",
        f"Skaters in fourth distance: {config.qualification_limit}",
        f"Reserves: {config.reserve_count}",
        f"Case number (seed): {config.seed}",
        f"Classification restriction: {'top ' + str(config.overall_rank_limit) if config.apply_overall_rank_limit else 'none'}",
        "",
        "RESULTS OF THE FIRST THREE DISTANCES",
    ]
    for distance in config.distances[:3]:
        lines.extend(["", f"{distance} m", "-" * 65])
        for _, row in distance_table(case, distance).iterrows():
            lines.append(f"{str(row['Rank'] or '-'):>3} | {row['Bib']:>3} | {row['Skater']:<26} | {row['Time / status']}")
    lines.extend(["", "PRACTICE QUESTIONS", "-" * 65])
    lines.extend(f"{i}. {question}" for i, question in enumerate(english_exercises(config, case), 1))
    lines.extend(["", "Calculate the standings and make your own selection before viewing the answer key."])
    return "\n".join(lines).encode("utf-8")


def instructor_exports(case: dict) -> tuple[bytes, bytes]:
    config = case["config"]
    exercises = english_exercises(config, case)
    # Reuse the English-language v18 exporter to preserve the data format.
    with tempfile.TemporaryDirectory() as directory:
        p = Path(directory)
        json_path = gen.save_json(
            case["skaters"], config, case["selected"], case["reserves"],
            exercises, case["incident_messages"], case["tie_messages"], p,
        )
        txt_path = gen.save_text_report(
            case["skaters"], config, case["selected"], case["reserves"],
            exercises, case["incident_messages"], case["tie_messages"], p,
        )
        return txt_path.read_bytes(), json_path.read_bytes()


def edit_results(case: dict) -> None:
    """Edit recorded times/statuses for one of the first three distances."""
    config = case["config"]
    distance = st.selectbox("Distance to edit", config.distances[:3])
    rows = [
        {
            "Bib": s.bib,
            "Skater": s.name,
            "Time (seconds)": s.times[distance],
            "Status": s.statuses[distance],
        }
        for s in sorted(case["skaters"], key=lambda x: x.bib)
    ]
    st.caption("Use times in seconds (e.g. 117.42). For DNS, DNF and WDR you can leave the time blank. "
               "Edits are applied only when you click Save changes.")
    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        disabled=["Bib", "Skater"],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status", options=["OK", "DNS", "DNF", "DQ", "WDR", "N/A"], required=True
            ),
            "Time (seconds)": st.column_config.NumberColumn(
                "Time (seconds)", min_value=0.01, step=0.01, format="%.2f"
            ),
        },
        key=f"editor_{st.session_state.get('revision', 0)}_{distance}",
    )

    if st.button("Save changes and recalculate", type="primary"):
        changes = []
        for row in edited.to_dict(orient="records"):
            bib = int(row["Bib"])
            status = row["Status"]
            raw = row["Time (seconds)"]
            time = None if pd.isna(raw) else round(float(raw), 2)
            if status in ("OK", "DQ") and (time is None or time <= 0):
                st.error(f"Bib {bib}: an OK or DQ result must have a valid time. No changes saved.")
                return
            changes.append((bib, status, time))

        # Work on a copy so invalid edits never partly overwrite a practice case.
        new_skaters = copy.deepcopy(case["skaters"])
        by_bib = {s.bib: s for s in new_skaters}
        for bib, status, time in changes:
            skater = by_bib[bib]
            if status in {"DNS", "WDR"}:
                gen.apply_incident_to_skater(skater, config.distances,
                                             config.distances.index(distance), status)
            elif status in {"DNF", "N/A"}:
                skater.statuses[distance] = status
                skater.times[distance] = None
            else:
                skater.statuses[distance] = status
                skater.times[distance] = time
        case["skaters"] = new_skaters
        case["edited"] = True
        case["incident_messages"] = []  # Notes from the original draw may no longer apply.
        case["tie_messages"] = []
        recalculate_selection(case)
        st.session_state["revision"] = st.session_state.get("revision", 0) + 1
        st.session_state["show_answer"] = False
        st.success("Changes saved. Standings and fourth-distance selection updated.")
        st.rerun()


# ─── User interface ──────────────────────────────────────────────────────────
st.title("⛸️ Allround Practice Case Generator")
st.caption("Practice the fourth-distance selection in an Allround Combination. Based on generator v18.")

with st.sidebar:
    st.header("Create a case")
    # Settings stay outside a Streamlit form so dependent controls react immediately.
    with st.container():
        gender_label = st.radio("Category", ["Men", "Women"], horizontal=True)
        gender = gender_label.lower()
        presets = gen.DISTANCE_PRESETS[gender]
        preset = st.selectbox("Allround combination", list(presets),
                              format_func=lambda name: f"{name.title()} — {' / '.join(map(str, presets[name]))} m")
        distances = presets[preset].copy()
        skaters_n = st.number_input("Number of skaters", min_value=10, max_value=40, value=24, step=1)
        max_qualifiers = int(skaters_n) - 2
        qualifiers = st.number_input("Skaters in fourth distance", min_value=2,
                                     max_value=max_qualifiers, value=min(8, max_qualifiers), step=1)
        reserve_n = st.number_input("Number of reserves", min_value=0,
                                    max_value=int(skaters_n) - int(qualifiers), value=min(2, int(skaters_n) - int(qualifiers)), step=1)
        st.markdown("**Selection restrictions**")
        top_x = st.checkbox("Apply classification top-X restriction")
        limit = st.number_input("Top-X limit", min_value=int(qualifiers), max_value=int(skaters_n),
                                value=min(int(skaters_n), max(int(qualifiers), 16)),
                                disabled=not top_x, step=1)
        trap = st.checkbox("Include an international top-X selection trap",
                           disabled=not top_x or int(limit) >= int(skaters_n))
        st.markdown("**Practice scenarios**")
        tie_label = st.selectbox("Tie scenario", list(TIE_LABELS))
        max_ties = st.number_input("Maximum tie positions", min_value=1, max_value=3, value=1,
                                   disabled=TIE_LABELS[tie_label] == "none", step=1)
        incidents = st.checkbox("Simulate DNS / DNF / DQ / WDR")
        incident_n = st.number_input("Number of incidents", min_value=1, max_value=4, value=2,
                                     disabled=not incidents, step=1)
        seed_text = st.text_input("Case number (optional)", placeholder="Blank = new random case")
        submitted = st.button("Generate practice case", type="primary", use_container_width=True)

    st.caption("Generated cases are fictional. Always check applicable ISU rules and competition documents.")

if submitted:
    try:
        case_seed = int(seed_text.strip()) if seed_text.strip() else secrets.randbelow(2_000_000_000)
        config = gen.TournamentConfig(
            gender=gender,
            distances=distances,
            number_of_skaters=int(skaters_n),
            qualification_limit=int(qualifiers),
            reserve_count=int(reserve_n),
            apply_overall_rank_limit=bool(top_x),
            overall_rank_limit=int(limit) if top_x else None,
            force_outside_top_x_longest_top_y=bool(top_x and int(limit) < int(skaters_n) and trap),
            tie_scenario=TIE_LABELS[tie_label],
            max_tie_positions=int(max_ties) if TIE_LABELS[tie_label] != "none" else 0,
            seed=case_seed,
            simulate_incidents=bool(incidents),
            incident_count=int(incident_n) if incidents else 0,
            create_exercises=True,
            save_outputs=False,
        )
        with st.spinner("Generating a realistic allround practice case..."):
            case = generate_case(config)
        st.session_state["case"] = case
        st.session_state["revision"] = st.session_state.get("revision", 0) + 1
        st.session_state["show_answer"] = False
    except ValueError as exc:
        st.error(f"Invalid settings or case number: {exc}")
    except Exception as exc:
        st.error(f"Could not generate the case: {exc}")

if "case" not in st.session_state:
    st.info("Choose your settings in the sidebar and click **Generate practice case**.")
    st.stop()

case = st.session_state["case"]
config = case["config"]

st.success(f"Case #{config.seed} generated — {config.gender.title()}, "
           f"{' / '.join(map(str, config.distances))} m")
a, b, c = st.columns(3)
a.metric("Skaters", len(case["skaters"]))
b.metric("Fourth-distance places", config.qualification_limit)
c.metric("Reserves", config.reserve_count)

results_tab, standings_tab, selection_tab, edit_tab, downloads_tab = st.tabs([
    "Race results", "Standings", "Selection exercise", "Edit results", "Downloads"
])

with results_tab:
    st.subheader("Results — first three distances")
    for distance in config.distances[:3]:
        with st.expander(f"{distance} m", expanded=distance == config.distances[0]):
            st.dataframe(distance_table(case, distance), hide_index=True, use_container_width=True)
    if case["incident_messages"] and not case["edited"]:
        with st.expander("Simulated incident notes"):
            for skater in case["skaters"]:
                issues = [f"{d} m: {skater.statuses[d]}" for d in config.distances
                          if skater.statuses[d] in ("DNS", "DNF", "DQ", "WDR")]
                if issues:
                    st.write(f"Bib {skater.bib} — {skater.name}: {', '.join(issues)}")

with standings_tab:
    st.subheader("Classification after two distances")
    st.dataframe(classification_table(case, 2), hide_index=True, use_container_width=True)
    st.subheader("Classification after three distances")
    st.dataframe(classification_table(case, 3), hide_index=True, use_container_width=True)
    st.caption("The rank on each distance is shown in parentheses after the time. "
               "Forced ties are attempted where possible, but may not be achievable for every case.")

with selection_tab:
    st.subheader("Your fourth-distance selection")
    st.write(f"Select the **{config.qualification_limit} skaters** who should qualify "
             f"for the {config.distances[3]} m, using the classification and "
             f"the longest completed distance ({max(config.distances[:3])} m).")
    if config.apply_overall_rank_limit:
        st.info(f"International restriction: only skaters in the top {config.overall_rank_limit} "
                "of the classification after three distances are eligible.")
    eligible = sorted(gen.eligible_skaters_after_3(case["skaters"]), key=lambda s: s.bib)
    bib_names = {s.bib: s.name for s in eligible}
    chosen = st.multiselect(
        "Your selection (bib numbers)", list(bib_names),
        format_func=lambda bib: f"{bib} — {bib_names[bib]}",
        max_selections=config.qualification_limit,
        key=f"practice_selection_{st.session_state['revision']}",
    )
    if st.button("Check my selection", type="primary"):
        if len(chosen) != config.qualification_limit:
            st.warning(f"Choose exactly {config.qualification_limit} skaters first.")
        else:
            correct = {s.bib for s in case["selected"]}
            missing = correct - set(chosen)
            incorrect = set(chosen) - correct
            if not missing and not incorrect:
                st.success("Correct selection! You have selected all qualifying skaters.")
            else:
                st.warning(f"Not quite: {len(missing)} qualifying skater(s) missing, "
                           f"and {len(incorrect)} selected skater(s) do not qualify.")

    if st.button("Reveal official selection and reserves"):
        st.session_state["show_answer"] = True
    if st.session_state.get("show_answer", False):
        st.subheader("Answer key — selected skaters")
        st.dataframe(selection_table(case["selected"]), hide_index=True, use_container_width=True)
        st.subheader("Reserves")
        if case["reserves"]:
            st.dataframe(selection_table(case["reserves"]), hide_index=True, use_container_width=True)
        else:
            st.write("No reserves selected.")

    with st.expander("Practice questions"):
        for number, q in enumerate(english_exercises(config, case), 1):
            st.write(f"{number}. {q}")

with edit_tab:
    st.subheader("Edit results and recalculate")
    st.warning("Changes to the first three distances may affect eligibility and selection. "
               "Editing can remove an originally generated tie or scenario; the selection is recalculated.")
    edit_results(case)

with downloads_tab:
    st.subheader("Student materials")
    st.download_button("Download practice worksheet (TXT)", practice_text(case),
                       file_name=f"allround_practice_{config.seed}.txt", mime="text/plain")
    st.download_button("Download race results (CSV)", practice_csv(case),
                       file_name=f"allround_results_{config.seed}.csv", mime="text/csv")

    st.subheader("Instructor materials")
    st.caption("These files include the answer key. Hide them from students until the exercise is complete.")
    if st.checkbox("Show instructor downloads"):
        full_txt, full_json = instructor_exports(case)
        st.download_button("Download instructor report (TXT)", full_txt,
                           file_name=f"allround_instructor_{config.seed}.txt", mime="text/plain")
        st.download_button("Download all case data (JSON)", full_json,
                           file_name=f"allround_case_{config.seed}.json", mime="application/json")
    st.info("To recreate this case, use the same settings and case number (seed). "
            "Manual edits are not encoded in the case number.")

st.divider()
st.caption("Unofficial training tool. Always verify exercises against current ISU regulations and the event-specific qualification documents.")
