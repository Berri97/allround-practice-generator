
"""Allround Practice Case Generator - Streamlit web app.

Keep allround_practice_case_generator_v18_EN.py in the same
GitHub repository. The generator handles all competition
calculations and fourth-distance selection rules.
"""

from __future__ import annotations

import copy
import json
import random
import secrets
import tempfile
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


# ============================================================
# CASE GENERATION
# ============================================================

def generate_case(config: gen.TournamentConfig) -> dict:
    """Generate a case using the existing v18 rules."""

    rng = random.Random(config.seed)
    skaters = None
    incident_messages = []
    tie_messages = []
    pending_fourth_incidents = []

    for _ in range(150):

        candidate = (
            gen.create_initial_skaters_with_selection_challenge(
                config, rng
            )
        )

        candidate_incidents = []
        candidate_pending = []

        if config.simulate_incidents:
            (
                candidate_incidents,
                candidate_pending,
            ) = gen.simulate_incidents(
                candidate,
                config.distances,
                config.incident_count,
                rng,
            )

        gen.recalculate_all(candidate, config.distances)

        candidate_ties = gen.apply_tie_scenario(
            candidate, config, rng
        )

        gen.recalculate_all(candidate, config.distances)

        challenge_ok = (
            gen.has_meaningful_fourth_distance_selection(
                candidate,
                config.qualification_limit,
                config.overall_rank_limit
                if config.apply_overall_rank_limit
                else None,
            )
        )

        trap_ok = True

        if (
            config.apply_overall_rank_limit
            and config.force_outside_top_x_longest_top_y
        ):
            trap_ok = gen.has_outside_top_x_longest_top_y_trap(
                candidate,
                config.overall_rank_limit,
                config.qualification_limit,
            )

        if challenge_ok and trap_ok:
            skaters = candidate
            incident_messages = candidate_incidents
            pending_fourth_incidents = candidate_pending
            tie_messages = candidate_ties
            break

    if skaters is None:
        raise RuntimeError(
            "No valid case could be generated. "
            "Try another case number, fewer incidents "
            "or less restrictive options."
        )

    selected, reserves = gen.select_for_fourth_distance(
        skaters,
        config.qualification_limit,
        config.reserve_count,
        config.overall_rank_limit
        if config.apply_overall_rank_limit
        else None,
    )

    incident_messages.extend(
        gen.apply_fourth_distance_incidents(
            selected,
            config.distances,
            pending_fourth_incidents,
            rng,
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


def recalculate_selection(case: dict) -> None:
    """Recalculate standings and selection after edits."""

    config = case["config"]

    gen.recalculate_all(
        case["skaters"],
        config.distances,
    )

    case["selected"], case["reserves"] = (
        gen.select_for_fourth_distance(
            case["skaters"],
            config.qualification_limit,
            config.reserve_count,
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None,
        )
    )


# ============================================================
# EXERCISE QUESTIONS
# ============================================================

def english_exercises(config, case) -> list[str]:

    longest = max(config.distances[:3])

    questions = [
        "Verify the classification after two distances, "
        "including ranks and total points.",

        "Determine the pairing and starting order "
        "for the third distance.",

        "Verify the classification after three distances, "
        "including ties and unclassified skaters.",

        f"Select {config.qualification_limit} skaters for "
        f"the fourth distance, considering both the "
        f"overall classification and the {longest} m result.",

        f"Prepare an ordered reserve list of "
        f"{config.reserve_count} skaters and explain "
        f"your choices.",

        "Prepare the start list for the fourth distance. "
        "Explain the pairings and starting order.",
    ]

    if case["tie_messages"]:
        questions.append(
            "Explain how each relevant tie affects "
            "the ranking and selection."
        )

    if case["incident_messages"]:
        questions.append(
            "For each incident, assess the consequences "
            "for eligibility and selection."
        )

    questions.append(
        "Which checks should the referee make "
        "before signing the start list?"
    )

    return questions


# ============================================================
# RESULTS AND CLASSIFICATION TABLES
# ============================================================

def distance_table(case, distance):

    rows = []

    for s in case["skaters"]:

        status = s.statuses[distance]

        if status == "OK":
            result = gen.format_time(s.times[distance])
        elif status == "N/A":
            result = "-"
        else:
            result = status

        rows.append({
            "Rank": s.distance_ranks.get(distance),
            "Bib": s.bib,
            "Skater": s.name,
            "Time / status": result,
            "Points": (
                f"{s.points[distance]:.3f}"
                if s.points[distance] is not None
                else "-"
            ),
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["Rank", "Bib"],
            na_position="last",
            kind="stable",
        )
        .reset_index(drop=True)
    )


def classification_table(case, count):

    rows = []

    ordered = sorted(
        case["skaters"],
        key=lambda s: gen.classification_sort_key(
            s, count
        ),
    )

    for s in ordered:

        if count == 2:
            rank = s.overall_rank_after_2
            total = s.total_points_after_2
        else:
            rank = s.overall_rank_after_3
            total = s.total_points_after_3

        row = {
            "Rank": rank,
            "Bib": s.bib,
            "Skater": s.name,
        }

        for distance in case["config"].distances[:count]:
            row[f"{distance} m"] = (
                gen.format_time_with_rank(s, distance)
            )

        row["Total points"] = (
            f"{total:.3f}"
            if total is not None
            else "-"
        )

        rows.append(row)

    return pd.DataFrame(rows)


def selection_table(skaters):

    return pd.DataFrame([
        {
            "No.": index,
            "Bib": s.bib,
            "Skater": s.name,
            "Classification rank": s.overall_rank_after_3,
            "Longest-distance rank": s.longest_distance_rank,
        }
        for index, s in enumerate(skaters, start=1)
    ])


# ============================================================
# OFFICIAL STARTING PAIRS
# ============================================================

def official_start_list(case):
    """
    Create the instructor answer key for the fourth distance.

    This follows the pairing model from the supplied
    fourth-distance draw script.

    Skaters are sorted by classification rank, then
    by longest-distance rank. Adjacent skaters are
    paired and the pair order is reversed.

    This teaching model must be checked against the
    applicable ISU rules and event instructions.
    """

    ranked = sorted(
        case["selected"],
        key=lambda s: (
            s.overall_rank_after_3
            if s.overall_rank_after_3 is not None
            else 999,

            s.longest_distance_rank
            if s.longest_distance_rank is not None
            else 999,

            s.bib,
        ),
    )

    pairs = []

    for i in range(0, len(ranked), 2):

        inner = ranked[i]

        outer = (
            ranked[i + 1]
            if i + 1 < len(ranked)
            else None
        )

        pairs.append((inner, outer))

    pairs.reverse()

    return pairs


def start_list_table(case):

    rows = []

    for number, (inner, outer) in enumerate(
        official_start_list(case),
        start=1,
    ):

        rows.append({
            "Pair": number,
            "Inner bib": inner.bib,
            "Inner skater": inner.name,
            "Outer bib": (
                outer.bib if outer else "-"
            ),
            "Outer skater": (
                outer.name if outer else "Solo"
            ),
        })

    return pd.DataFrame(rows)


# ============================================================
# PARTICIPANT PAIR ANSWER CHECKING
# ============================================================

def evaluate_student_pairs(
    entries,
    chosen_bibs,
    case,
):
    """
    Check the number of pairs, skater selection,
    pair order and lane assignments.
    """

    required = len(case["selected"])
    expected_count = (required + 1) // 2

    errors = []

    if len(chosen_bibs) != required:
        errors.append(
            f"First select {required} skaters "
            "for the fourth distance."
        )

    if len(entries) != expected_count:
        errors.append(
            "The number of pairs is not correct."
        )

    all_bibs = [
        bib
        for inner, outer in entries
        for bib in (inner, outer)
        if bib is not None
    ]

    if any(inner is None for inner, outer in entries):
        errors.append(
            "Choose an inner-lane skater for every pair."
        )

    if len(all_bibs) != len(set(all_bibs)):
        errors.append(
            "A skater can only appear once "
            "in the start list."
        )

    if len(all_bibs) != required:
        errors.append(
            f"Enter all {required} skaters "
            "in the start list."
        )

    if (
        len(chosen_bibs) == required
        and set(all_bibs) != set(chosen_bibs)
    ):
        errors.append(
            "The start list must contain exactly "
            "the skaters you selected."
        )

    if errors:
        return {
            "valid": False,
            "correct": False,
            "errors": errors,
            "correct_count": 0,
        }

    expected = [
        (
            inner.bib,
            outer.bib if outer else None,
        )
        for inner, outer in official_start_list(case)
    ]

    correct_count = sum(
        entered == correct
        for entered, correct in zip(entries, expected)
    )

    correct_selection = (
        set(chosen_bibs)
        == {s.bib for s in case["selected"]}
    )

    return {
        "valid": True,
        "correct": (
            correct_selection and entries == expected
        ),
        "correct_count": correct_count,
        "total_pairs": len(expected),
        "correct_selection": correct_selection,
        "errors": [],
    }


# ============================================================
# DYNAMIC PAIR EDITOR
# ============================================================

def prepare_pair_editor(revision):
    """
    Start with one empty pair.
    Keep row IDs stable when Streamlit reruns.
    """

    rows_key = f"practice_pair_rows_{revision}"
    next_key = f"practice_pair_next_id_{revision}"

    if rows_key not in st.session_state:

        st.session_state[rows_key] = [0]
        st.session_state[next_key] = 1

    return rows_key, next_key


def reset_pair_feedback(revision):

    st.session_state[
        f"pair_feedback_{revision}"
    ] = None

    st.session_state[
        f"reveal_pairs_{revision}"
    ] = False


def add_student_pair(revision):

    rows_key, next_key = prepare_pair_editor(revision)

    new_id = st.session_state[next_key]

    st.session_state[rows_key].append(new_id)

    st.session_state[next_key] = new_id + 1

    reset_pair_feedback(revision)


def remove_student_pair(revision):

    rows_key, _ = prepare_pair_editor(revision)

    rows = st.session_state[rows_key]

    if len(rows) <= 1:
        return

    removed_id = rows.pop()

    st.session_state.pop(
        f"pair_inner_{revision}_{removed_id}",
        None,
    )

    st.session_state.pop(
        f"pair_outer_{revision}_{removed_id}",
        None,
    )

    reset_pair_feedback(revision)


def pair_exercise(case, eligible, chosen):
    """
    Participant creates the start list manually.

    One pair is visible initially.
    Additional pairs are added using the plus button.
    """

    revision = st.session_state["revision"]

    rows_key, _ = prepare_pair_editor(revision)

    st.subheader(
        "Create the starting pairs"
    )

    st.write(
        "Create the start list for the fourth distance. "
        "Start with one pair and click **+ Add pair** "
        "to create the next pair."
    )

    st.caption(
        "Choose the inner lane (I) and outer lane (O). "
        "For a solo pair, leave the outer lane empty."
    )

    bib_names = {
        s.bib: s.name
        for s in eligible
    }

    possible_bibs = [
        None,
        *sorted(bib_names),
    ]

    def display_skater(bib):

        if bib is None:
            return "— Choose skater —"

        return f"{bib} — {bib_names[bib]}"

    entered_pairs = []

    for number, row_id in enumerate(
        st.session_state[rows_key],
        start=1,
    ):

        pair_col, inner_col, outer_col = st.columns(
            [1, 4, 4]
        )

        with pair_col:
            st.markdown(
                f"**Pair {number}**"
            )

        with inner_col:

            inner = st.selectbox(
                "Inner lane (I)",
                possible_bibs,
                format_func=display_skater,
                key=f"pair_inner_{revision}_{row_id}",
                on_change=reset_pair_feedback,
                args=(revision,),
            )

        with outer_col:

            outer = st.selectbox(
                "Outer lane (O)",
                possible_bibs,
                format_func=display_skater,
                key=f"pair_outer_{revision}_{row_id}",
                on_change=reset_pair_feedback,
                args=(revision,),
            )

        entered_pairs.append(
            (inner, outer)
        )

    st.divider()

    add_col, remove_col = st.columns(2)

    with add_col:

        st.button(
            "＋ Add pair",
            on_click=add_student_pair,
            args=(revision,),
            key=f"add_pair_{revision}",
            use_container_width=True,
        )

    with remove_col:

        st.button(
            "− Remove last pair",
            on_click=remove_student_pair,
            args=(revision,),
            disabled=(
                len(st.session_state[rows_key]) == 1
            ),
            key=f"remove_pair_{revision}",
            use_container_width=True,
        )

    st.divider()

    if st.button(
        "Check my starting pairs",
        type="primary",
        key=f"check_pairs_{revision}",
    ):

        result = evaluate_student_pairs(
            entered_pairs,
            chosen,
            case,
        )

        st.session_state[
            f"pair_feedback_{revision}"
        ] = result

        st.session_state[
            f"reveal_pairs_{revision}"
        ] = False

    feedback = st.session_state.get(
        f"pair_feedback_{revision}"
    )

    if feedback is not None:

        if feedback["errors"]:

            for error in feedback["errors"]:
                st.warning(error)

        elif feedback["correct"]:

            st.success(
                "Correct! All skaters, pairs "
                "and lane positions are right."
            )

        else:

            st.warning(
                f"{feedback['correct_count']} of "
                f"{feedback['total_pairs']} pairs "
                "are correct."
            )

            if not feedback["correct_selection"]:
                st.info(
                    "Check your selection for "
                    "the fourth distance as well."
                )

        if st.button(
            "Show correct starting pairs",
            key=f"reveal_pairs_button_{revision}",
        ):

            st.session_state[
                f"reveal_pairs_{revision}"
            ] = True

    if st.session_state.get(
        f"reveal_pairs_{revision}",
        False,
    ):

        st.subheader(
            "Correct starting pairs"
        )

        st.dataframe(
            start_list_table(case),
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# PARTICIPANT EXPORTS
# ============================================================

def practice_csv(case):

    config = case["config"]

    rows = []

    for distance in config.distances[:3]:

        for s in case["skaters"]:

            rows.append({
                "distance_m": distance,
                "bib": s.bib,
                "name": s.name,
                "status": s.statuses[distance],
                "time_s": (
                    s.times[distance]
                    if s.statuses[distance] == "OK"
                    else ""
                ),
            })

    return (
        pd.DataFrame(rows)
        .to_csv(index=False)
        .encode("utf-8-sig")
    )


def practice_text(case):

    config = case["config"]

    lines = [
        "ALLROUND PRACTICE CASE — PARTICIPANT WORKSHEET",
        "=" * 65,
        f"Category: {config.gender.title()}",
        f"Distances: {' / '.join(map(str, config.distances))} m",
        f"Skaters in fourth distance: {config.qualification_limit}",
        f"Reserves: {config.reserve_count}",
        f"Case number: {config.seed}",
        "",
        "RESULTS OF THE FIRST THREE DISTANCES",
    ]

    for distance in config.distances[:3]:

        lines.extend([
            "",
            f"{distance} m",
            "-" * 65,
        ])

        table = distance_table(case, distance)

        for _, row in table.iterrows():

            rank = row["Rank"]

            rank_text = (
                "-"
                if pd.isna(rank)
                else str(int(rank))
            )

            lines.append(
                f"{rank_text:>3} | "
                f"{int(row['Bib']):>3} | "
                f"{row['Skater']:<26} | "
                f"{row['Time / status']}"
            )

    lines.extend([
        "",
        "PRACTICE QUESTIONS",
        "-" * 65,
    ])

    questions = english_exercises(config, case)

    for number, question in enumerate(
        questions, start=1
    ):

        lines.append(
            f"{number}. {question}"
        )

    return "\n".join(lines).encode("utf-8")


# ============================================================
# INSTRUCTOR EXPORTS
# ============================================================

def instructor_exports(case):

    config = case["config"]

    exercises = english_exercises(
        config, case
    )

    with tempfile.TemporaryDirectory() as directory:

        output_dir = Path(directory)

        json_path = gen.save_json(
            case["skaters"],
            config,
            case["selected"],
            case["reserves"],
            exercises,
            case["incident_messages"],
            case["tie_messages"],
            output_dir,
        )

        txt_path = gen.save_text_report(
            case["skaters"],
            config,
            case["selected"],
            case["reserves"],
            exercises,
            case["incident_messages"],
            case["tie_messages"],
            output_dir,
        )

        report = txt_path.read_text(
            encoding="utf-8"
        ).rstrip()

        report += (
            "\n\nFOURTH DISTANCE — OFFICIAL START LIST\n"
            + "-" * 65
            + "\n"
        )

        for number, (inner, outer) in enumerate(
            official_start_list(case),
            start=1,
        ):

            report += (
                f"Pair {number}: "
                f"I — {inner.bib} {inner.name} | "
            )

            if outer:
                report += (
                    f"O — {outer.bib} {outer.name}\n"
                )
            else:
                report += "O — Solo\n"

        payload = json.loads(
            json_path.read_text(encoding="utf-8")
        )

        payload["fourth_distance_start_list"] = (
            start_list_table(case)
            .to_dict(orient="records")
        )

        report_bytes = (
            report + "\n"
        ).encode("utf-8")

        json_bytes = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        return report_bytes, json_bytes


# ============================================================
# EDIT RESULTS
# ============================================================

def edit_results(case):

    config = case["config"]

    distance = st.selectbox(
        "Distance to edit",
        config.distances[:3],
    )

    rows = []

    for s in sorted(
        case["skaters"],
        key=lambda x: x.bib,
    ):

        rows.append({
            "Bib": s.bib,
            "Skater": s.name,
            "Time (seconds)": s.times[distance],
            "Status": s.statuses[distance],
        })

    st.caption(
        "Enter times in seconds, for example 117.42. "
        "Click Save changes to update the results."
    )

    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        use_container_width=True,
        disabled=["Bib", "Skater"],
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Status",
                options=[
                    "OK",
                    "DNS",
                    "DNF",
                    "DQ",
                    "WDR",
                    "N/A",
                ],
                required=True,
            ),

            "Time (seconds)": (
                st.column_config.NumberColumn(
                    "Time (seconds)",
                    min_value=0.01,
                    step=0.01,
                    format="%.2f",
                )
            ),
        },
        key=(
            f"editor_"
            f"{st.session_state.get('revision', 0)}_"
            f"{distance}"
        ),
    )

    if st.button(
        "Save changes and recalculate",
        type="primary",
    ):

        changes = []

        for row in edited.to_dict(
            orient="records"
        ):

            bib = int(row["Bib"])
            status = row["Status"]
            raw = row["Time (seconds)"]

            time = (
                None
                if pd.isna(raw)
                else round(float(raw), 2)
            )

            if (
                status in ("OK", "DQ")
                and (time is None or time <= 0)
            ):

                st.error(
                    f"Bib {bib}: a valid time is required."
                )
                return

            changes.append(
                (bib, status, time)
            )

        new_skaters = copy.deepcopy(
            case["skaters"]
        )

        by_bib = {
            s.bib: s
            for s in new_skaters
        }

        for bib, status, time in changes:

            skater = by_bib[bib]

            if status in {"DNS", "WDR"}:

                gen.apply_incident_to_skater(
                    skater,
                    config.distances,
                    config.distances.index(distance),
                    status,
                )

            elif status in {"DNF", "N/A"}:

                skater.statuses[distance] = status
                skater.times[distance] = None

            else:

                skater.statuses[distance] = status
                skater.times[distance] = time

        case["skaters"] = new_skaters
        case["edited"] = True
        case["incident_messages"] = []
        case["tie_messages"] = []

        recalculate_selection(case)

        st.session_state["revision"] = (
            st.session_state.get("revision", 0) + 1
        )

        st.session_state["show_answer"] = False

        st.success(
            "Changes saved. Standings and selection updated."
        )

        st.rerun()


# ============================================================
# USER INTERFACE
# ============================================================

st.title(
    "⛸️ Allround Practice Case Generator"
)

st.caption(
    "Practice the fourth-distance selection "
    "in an Allround Combination."
)


# ============================================================
# SIDEBAR - CASE SETTINGS
# ============================================================

with st.sidebar:

    st.header("Create a case")

    gender_label = st.radio(
        "Category",
        ["Men", "Women"],
        horizontal=True,
    )

    gender = gender_label.lower()

    presets = gen.DISTANCE_PRESETS[gender]

    preset = st.selectbox(
        "Allround combination",
        list(presets),
        format_func=lambda name: (
            f"{name.title()} — "
            f"{' / '.join(map(str, presets[name]))} m"
        ),
    )

    distances = presets[preset].copy()

    skaters_n = st.number_input(
        "Number of skaters",
        min_value=10,
        max_value=40,
        value=24,
        step=1,
    )

    max_qualifiers = int(skaters_n) - 2

    qualifiers = st.number_input(
        "Skaters in fourth distance",
        min_value=2,
        max_value=max_qualifiers,
        value=min(8, max_qualifiers),
        step=1,
    )

    reserve_n = st.number_input(
        "Number of reserves",
        min_value=0,
        max_value=(
            int(skaters_n) - int(qualifiers)
        ),
        value=min(
            2,
            int(skaters_n) - int(qualifiers),
        ),
        step=1,
    )

    st.markdown(
        "**Selection restrictions**"
    )

    top_x = st.checkbox(
        "Apply classification top-X restriction"
    )

    limit = st.number_input(
        "Top-X limit",
        min_value=int(qualifiers),
        max_value=int(skaters_n),
        value=min(
            int(skaters_n),
            max(int(qualifiers), 16),
        ),
        disabled=not top_x,
        step=1,
    )

    trap = st.checkbox(
        "Include an international top-X selection trap",
        disabled=(
            not top_x
            or int(limit) >= int(skaters_n)
        ),
    )

    st.markdown(
        "**Practice scenarios**"
    )

    tie_label = st.selectbox(
        "Tie scenario",
        list(TIE_LABELS),
    )

    max_ties = st.number_input(
        "Maximum tie positions",
        min_value=1,
        max_value=3,
        value=1,
        disabled=(
            TIE_LABELS[tie_label] == "none"
        ),
        step=1,
    )

    incidents = st.checkbox(
        "Simulate DNS / DNF / DQ / WDR"
    )

    incident_n = st.number_input(
        "Number of incidents",
        min_value=1,
        max_value=4,
        value=2,
        disabled=not incidents,
        step=1,
    )

    seed_text = st.text_input(
        "Case number (optional)",
        placeholder="Blank = new random case",
    )

    submitted = st.button(
        "Generate practice case",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "Generated cases are fictional. "
        "Always check the applicable ISU Rules "
        "and competition documents."
    )


# ============================================================
# GENERATE CASE
# ============================================================

if submitted:

    try:

        case_seed = (
            int(seed_text.strip())
            if seed_text.strip()
            else secrets.randbelow(2_000_000_000)
        )

        config = gen.TournamentConfig(
            gender=gender,
            distances=distances,
            number_of_skaters=int(skaters_n),
            qualification_limit=int(qualifiers),
            reserve_count=int(reserve_n),
            apply_overall_rank_limit=bool(top_x),
            overall_rank_limit=(
                int(limit) if top_x else None
            ),
            force_outside_top_x_longest_top_y=bool(
                top_x
                and int(limit) < int(skaters_n)
                and trap
            ),
            tie_scenario=TIE_LABELS[tie_label],
            max_tie_positions=(
                int(max_ties)
                if TIE_LABELS[tie_label] != "none"
                else 0
            ),
            seed=case_seed,
            simulate_incidents=bool(incidents),
            incident_count=(
                int(incident_n) if incidents else 0
            ),
            create_exercises=True,
            save_outputs=False,
        )

        with st.spinner(
            "Generating a realistic allround practice case..."
        ):

            case = generate_case(config)

        st.session_state["case"] = case

        st.session_state["revision"] = (
            st.session_state.get("revision", 0) + 1
        )

        st.session_state["show_answer"] = False

    except ValueError as exc:

        st.error(
            f"Invalid settings or case number: {exc}"
        )

    except Exception as exc:

        st.error(
            f"Could not generate the case: {exc}"
        )


if "case" not in st.session_state:

    st.info(
        "Choose your settings in the sidebar "
        "and click **Generate practice case**."
    )

    st.stop()


case = st.session_state["case"]
config = case["config"]

st.success(
    f"Case #{config.seed} generated — "
    f"{config.gender.title()}, "
    f"{' / '.join(map(str, config.distances))} m"
)

a, b, c = st.columns(3)

a.metric(
    "Skaters",
    len(case["skaters"]),
)

b.metric(
    "Fourth-distance places",
    config.qualification_limit,
)

c.metric(
    "Reserves",
    config.reserve_count,
)


# ============================================================
# TABS
# ============================================================

(
    results_tab,
    standings_tab,
    selection_tab,
    edit_tab,
    downloads_tab,
) = st.tabs([
    "Race results",
    "Standings",
    "Selection exercise",
    "Edit results",
    "Downloads",
])


# ============================================================
# RACE RESULTS
# ============================================================

with results_tab:

    st.subheader(
        "Results — first three distances"
    )

    for distance in config.distances[:3]:

        with st.expander(
            f"{distance} m",
            expanded=(
                distance == config.distances[0]
            ),
        ):

            st.dataframe(
                distance_table(case, distance),
                hide_index=True,
                use_container_width=True,
            )

    if case["incident_messages"] and not case["edited"]:

        with st.expander(
            "Simulated incident notes"
        ):

            for s in case["skaters"]:

                issues = [
                    f"{d} m: {s.statuses[d]}"
                    for d in config.distances
                    if s.statuses[d] in (
                        "DNS", "DNF", "DQ", "WDR"
                    )
                ]

                if issues:

                    st.write(
                        f"Bib {s.bib} — {s.name}: "
                        + ", ".join(issues)
                    )


# ============================================================
# STANDINGS
# ============================================================

with standings_tab:

    st.subheader(
        "Classification after two distances"
    )

    st.dataframe(
        classification_table(case, 2),
        hide_index=True,
        use_container_width=True,
    )

    st.subheader(
        "Classification after three distances"
    )

    st.dataframe(
        classification_table(case, 3),
        hide_index=True,
        use_container_width=True,
    )


# ============================================================
# PARTICIPANT - SELECTION AND PAIRS
# ============================================================

with selection_tab:

    st.subheader(
        "Your fourth-distance selection"
    )

    st.write(
        f"Select the **{config.qualification_limit} "
        f"skaters** who should qualify for the "
        f"{config.distances[3]} m."
    )

    st.write(
        "Use the classification after three distances "
        "and the result of the longest completed distance."
    )

    if config.apply_overall_rank_limit:

        st.info(
            f"Only skaters in the top "
            f"{config.overall_rank_limit} of the "
            "classification after three distances "
            "are eligible."
        )

    eligible = sorted(
        gen.eligible_skaters_after_3(
            case["skaters"]
        ),
        key=lambda s: s.bib,
    )

    bib_names = {
        s.bib: s.name
        for s in eligible
    }

    chosen = st.multiselect(
        "Your selection (bib numbers)",
        list(bib_names),
        format_func=lambda bib: (
            f"{bib} — {bib_names[bib]}"
        ),
        max_selections=config.qualification_limit,
        key=(
            f"practice_selection_"
            f"{st.session_state['revision']}"
        ),
        on_change=reset_pair_feedback,
        args=(st.session_state["revision"],),
    )

    if st.button(
        "Check my selection",
        type="primary",
    ):

        if len(chosen) != config.qualification_limit:

            st.warning(
                f"Choose exactly "
                f"{config.qualification_limit} skaters."
            )

        else:

            correct = {
                s.bib
                for s in case["selected"]
            }

            missing = correct - set(chosen)

            incorrect = set(chosen) - correct

            if not missing and not incorrect:

                st.success(
                    "Correct selection! "
                    "You selected all qualifying skaters."
                )

            else:

                st.warning(
                    f"{len(missing)} qualifying skater(s) "
                    "are missing, and "
                    f"{len(incorrect)} selected skater(s) "
                    "do not qualify."
                )

    if st.button(
        "Reveal official selection and reserves"
    ):

        st.session_state["show_answer"] = True

    if st.session_state.get(
        "show_answer", False
    ):

        st.subheader(
            "Answer key — selected skaters"
        )

        st.dataframe(
            selection_table(case["selected"]),
            hide_index=True,
            use_container_width=True,
        )

        st.subheader("Reserves")

        if case["reserves"]:

            st.dataframe(
                selection_table(case["reserves"]),
                hide_index=True,
                use_container_width=True,
            )

        else:

            st.write(
                "No reserves selected."
            )

    st.divider()

    # Interactive pair exercise
    pair_exercise(
        case,
        eligible,
        chosen,
    )

    with st.expander(
        "Practice questions"
    ):

        for number, question in enumerate(
            english_exercises(config, case),
            start=1,
        ):

            st.write(
                f"{number}. {question}"
            )


# ============================================================
# EDIT RESULTS
# ============================================================

with edit_tab:

    st.subheader(
        "Edit results and recalculate"
    )

    st.warning(
        "Changes may affect eligibility and selection. "
        "The classification and selection will be recalculated."
    )

    edit_results(case)


# ============================================================
# DOWNLOADS
# ============================================================

with downloads_tab:

    st.subheader(
        "Participant materials"
    )

    st.download_button(
        "Download practice worksheet (TXT)",
        practice_text(case),
        file_name=(
            f"allround_practice_{config.seed}.txt"
        ),
        mime="text/plain",
    )

    st.download_button(
        "Download race results (CSV)",
        practice_csv(case),
        file_name=(
            f"allround_results_{config.seed}.csv"
        ),
        mime="text/csv",
    )

    st.divider()

    st.subheader(
        "Instructor materials"
    )

    st.caption(
        "Includes the complete selection, reserves "
        "and official starting pairs. "
        "Instructor login protection is not yet enabled."
    )

    if st.checkbox(
        "Show instructor materials"
    ):

        st.markdown(
            "**Official start list — fourth distance**"
        )

        st.dataframe(
            start_list_table(case),
            hide_index=True,
            use_container_width=True,
        )

        full_txt, full_json = instructor_exports(case)

        st.download_button(
            "Download instructor report (TXT)",
            full_txt,
            file_name=(
                f"allround_instructor_{config.seed}.txt"
            ),
            mime="text/plain",
        )

        st.download_button(
            "Download complete case data (JSON)",
            full_json,
            file_name=(
                f"allround_case_{config.seed}.json"
            ),
            mime="application/json",
        )

    st.info(
        "Use the same case number and settings "
        "to recreate the original generated case. "
        "Manual edits are not included in the case number."
    )


st.divider()

st.caption(
    "Unofficial training tool. Always verify the "
    "results against the current ISU Regulations "
    "and competition-specific instructions."
)
