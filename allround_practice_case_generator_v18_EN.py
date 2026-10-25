from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

TieScenario = Literal[
    "none",
    "classification",
    "longest_distance",
    "both",
    "qualification_boundary",
]

CompetitionGender = Literal["men", "women"]

RaceStatus = Literal[
    "OK",
    "DNS",
    "DNF",
    "DQ",
    "WDR",
    "N/A",
]


# =============================================================================
# FICTIONAL, INCLUSIVE NAME SETS
# =============================================================================

FICTIONAL_WOMEN_NAMES = [
    "Lina van Aken",
    "Noor El Amrani",
    "Sofia Petrovic",
    "Aya Nakamori",
    "Mila de Wit",
    "Fatima Rahmani",
    "Yara Mensah",
    "Elin Söderberg",
    "Amara Okafor",
    "Lotte Vermeer",
    "Inès Dubois",
    "Sara Jansen",
    "Nadia Kowalska",
    "Mei-Ling Chen",
    "Eva Lindström",
    "Rania Haddad",
    "Zoë van Dalen",
    "Leila Benali",
    "Nora Andersen",
    "Iris Hoekstra",
    "Samira Diallo",
    "Marta Nowak",
    "Hana Kovač",
    "Aisha Williams",
    "Liv de Graaf",
    "Camila Ribeiro",
    "Anika Sharma",
    "Eleni Papadopoulos",
    "Mariam Tesfaye",
    "Julie Martens",
    "Sanne Kuiper",
    "Alina Popescu",
    "Nour Abdi",
    "Chiara Rossi",
    "Lucía Moreno",
    "Daria Ivanova",
    "Maëlle Laurent",
    "Amina Yusuf",
    "Keira O'Connell",
    "Tess van Loon",
]

FICTIONAL_MEN_NAMES = [
    "Luca van Aken",
    "Omar El Amrani",
    "Milan Petrovic",
    "Haruto Nakamori",
    "Daan de Wit",
    "Yassin Rahmani",
    "Kwame Mensah",
    "Erik Söderberg",
    "Chidi Okafor",
    "Jasper Vermeer",
    "Mathis Dubois",
    "Sam Jansen",
    "Jakub Kowalski",
    "Wei Chen",
    "Nils Lindström",
    "Karim Haddad",
    "Finn van Dalen",
    "Adam Benali",
    "Mikkel Andersen",
    "Thijs Hoekstra",
    "Moussa Diallo",
    "Piotr Nowak",
    "Ivan Kovač",
    "Malik Williams",
    "Bram de Graaf",
    "Gabriel Ribeiro",
    "Arjun Sharma",
    "Nikos Papadopoulos",
    "Dawit Tesfaye",
    "Julien Martens",
    "Sven Kuiper",
    "Andrei Popescu",
    "Idris Abdi",
    "Marco Rossi",
    "Diego Moreno",
    "Dmitri Ivanov",
    "Louis Laurent",
    "Khalid Yusuf",
    "Sean O'Connell",
    "Timo van Loon",
]


# =============================================================================
# DISTANCE PRESETS
# =============================================================================

DISTANCE_PRESETS: dict[CompetitionGender, dict[str, list[int]]] = {
    "women": {
        "mini": [500, 1500, 1000, 3000],
        "large": [500, 3000, 1500, 5000],
    },
    "men": {
        "mini": [500, 1500, 1000, 3000],
        "small": [500, 3000, 1500, 5000],
        "large": [500, 5000, 1500, 10000],
    },
}

SUPPORTED_DISTANCES = {
    500,
    1000,
    1500,
    3000,
    5000,
    10000,
}


# =============================================================================
# REFERENCE TIMES
# =============================================================================

REFERENCE_TIMES: dict[CompetitionGender, dict[int, float]] = {
    "women": {
        500: 39.20,
        1000: 78.80,
        1500: 118.50,
        3000: 247.00,
        5000: 420.00,
        10000: 875.00,
    },
    "men": {
        500: 35.80,
        1000: 71.80,
        1500: 108.00,
        3000: 224.00,
        5000: 382.00,
        10000: 790.00,
    },
}


# =============================================================================
# DATA MODEL
# =============================================================================

@dataclass
class Skater:
    bib: int
    name: str
    ability: float
    endurance_bias: float = 0.0

    times: dict[int, float | None] = field(default_factory=dict)
    points: dict[int, float | None] = field(default_factory=dict)
    statuses: dict[int, RaceStatus] = field(default_factory=dict)
    distance_ranks: dict[int, int | None] = field(default_factory=dict)

    total_points_after_2: float | None = None
    total_points_after_3: float | None = None

    overall_rank_after_2: int | None = None
    overall_rank_after_3: int | None = None
    longest_distance_rank: int | None = None

    eligible_after_2: bool = True
    eligible_after_3: bool = True


@dataclass
class TournamentConfig:
    gender: CompetitionGender
    distances: list[int]
    number_of_skaters: int
    qualification_limit: int
    reserve_count: int
    apply_overall_rank_limit: bool
    overall_rank_limit: int | None
    force_outside_top_x_longest_top_y: bool
    tie_scenario: TieScenario
    max_tie_positions: int
    seed: int | None
    simulate_incidents: bool
    incident_count: int
    create_exercises: bool
    save_outputs: bool


# =============================================================================
# BASIC HELPERS
# =============================================================================

def points_for_distance(time_seconds: float, distance: int) -> float:
    return time_seconds * 500 / distance


def format_time(seconds: float | None) -> str:
    if seconds is None:
        return "-"

    minutes = int(seconds // 60)
    remainder = seconds % 60

    if minutes:
        return f"{minutes}:{remainder:05.2f}"

    return f"{remainder:.2f}"


def ask_choice(prompt: str, valid_choices: set[str]) -> str:
    while True:
        answer = input(prompt).strip().lower()

        if answer in valid_choices:
            return answer

        print(
            "Invalid choice. Select from: "
            + ", ".join(sorted(valid_choices))
        )


def ask_yes_no(prompt: str) -> bool:
    answer = ask_choice(prompt, {"j", "n", "ja", "no", "y", "yes", "no"})
    return answer in {"j", "ja", "y", "yes"}


def ask_integer(
    prompt: str,
    minimum: int,
    maximum: int,
) -> int:
    while True:
        try:
            value = int(input(prompt).strip())
        except ValueError:
            print("Enter a valid whole number.")
            continue

        if minimum <= value <= maximum:
            return value

        print(
            f"Enter a number from {minimum} "
            f"en maximaal {maximum}."
        )


def ask_optional_integer(prompt: str) -> int | None:
    while True:
        answer = input(prompt).strip()

        if answer == "":
            return None

        try:
            return int(answer)
        except ValueError:
            print("Enter a whole number or press Enter.")


# =============================================================================
# RANKING HELPERS
# =============================================================================

def competition_ranks(
    values: list[tuple[int, float]],
    decimals: int = 3,
) -> dict[int, int]:
    """
    Competition ranking:
    1, 2, 2, 4
    """
    sorted_values = sorted(values, key=lambda item: item[1])

    ranks: dict[int, int] = {}
    previous_value: float | None = None
    previous_rank = 0

    for index, (bib, value) in enumerate(sorted_values, start=1):
        rounded_value = round(value, decimals)

        if previous_value is None or rounded_value != previous_value:
            previous_rank = index
            previous_value = rounded_value

        ranks[bib] = previous_rank

    return ranks


def status_sort_key(status: RaceStatus) -> int:
    order = {
        "OK": 0,
        "DNF": 1,
        "DQ": 2,
        "DNS": 3,
        "WDR": 4,
        "N/A": 5,
    }
    return order.get(status, 99)


# =============================================================================
# USER CHOICES
# =============================================================================

def choose_gender() -> CompetitionGender:
    print("\nSELECT COMPETITION CATEGORY")
    print("1. Women")
    print("2. Men")

    choice = ask_choice("Select [1/2]: ", {"1", "2"})
    return "women" if choice == "1" else "men"


def choose_distances(gender: CompetitionGender) -> list[int]:
    print("\nSELECT THE ALLROUND COMBINATION")

    if gender == "women":
        print("1. Mini combination:  500 - 1500 - 1000 - 3000")
        print("2. Large combination: 500 - 3000 - 1500 - 5000")
        valid_choices = {"1", "2", "4"}
    else:
        print("1. Mini combination:  500 - 1500 - 1000 - 3000")
        print("2. Small combination: 500 - 3000 - 1500 - 5000")
        print("3. Large combination: 500 - 5000 - 1500 - 10000")
        valid_choices = {"1", "2", "3", "4"}

    print("4. Enter four distances manually")

    choice = ask_choice("Select: ", valid_choices)

    if choice == "4":
        return enter_distances_manually()

    if gender == "women":
        return (
            DISTANCE_PRESETS["women"]["mini"].copy()
            if choice == "1"
            else DISTANCE_PRESETS["women"]["large"].copy()
        )

    if choice == "1":
        return DISTANCE_PRESETS["men"]["mini"].copy()
    if choice == "2":
        return DISTANCE_PRESETS["men"]["small"].copy()
    return DISTANCE_PRESETS["men"]["large"].copy()


def enter_distances_manually() -> list[int]:
    print("\nMANUAL DISTANCE ENTRY")
    print(
        "Supported distances: "
        + ", ".join(str(d) for d in sorted(SUPPORTED_DISTANCES))
    )

    while True:
        raw_value = input(
            "Voer precies vier afstanden in, gescheiden door komma's\n"
            "Bijvoorbeeld 500,3000,1500,5000: "
        ).strip()

        try:
            distances = [
                int(value.strip())
                for value in raw_value.split(",")
            ]
        except ValueError:
            print("Use whole numbers only.")
            continue

        if len(distances) != 4:
            print("You must enter exactly four distances.")
            continue

        unsupported = [
            distance
            for distance in distances
            if distance not in SUPPORTED_DISTANCES
        ]

        if unsupported:
            print(
                "Unsupported distance(s): "
                + ", ".join(str(d) for d in unsupported)
            )
            continue

        print(
            "Let op: bij handmatige invoer controleert het script alleen "
            "of de afstanden technisch ondersteund worden."
        )
        return distances


def choose_tie_scenario() -> TieScenario:
    print("\nSELECT THE TIE SCENARIO")
    print("1. No forced tie")
    print("2. Tie in the classification after three distances")
    print("3. Tie in the result of the longest distance")
    print("4. Tie in both rankings")
    print("5. Tie around the selection cut-off")

    choice = ask_choice(
        "Maak een keuze [1-5]: ",
        {"1", "2", "3", "4", "5"},
    )

    scenarios: dict[str, TieScenario] = {
        "1": "none",
        "2": "classification",
        "3": "longest_distance",
        "4": "both",
        "5": "qualification_boundary",
    }

    return scenarios[choice]


def build_config() -> TournamentConfig:
    gender = choose_gender()
    distances = choose_distances(gender)

    available_names = (
        FICTIONAL_WOMEN_NAMES
        if gender == "women"
        else FICTIONAL_MEN_NAMES
    )

    number_of_skaters = ask_integer(
        f"\nHow many Skaters? [10-{len(available_names)}]: ",
        10,
        len(available_names),
    )

    qualification_limit = ask_integer(
        "How many Skaters may compete in the fourth distance? "
        f"[2-{number_of_skaters - 2}]: ",
        2,
        number_of_skaters - 2,
    )

    reserve_count = ask_integer(
        "How many reserve Skaters should be shown? "
        f"[0-{number_of_skaters - qualification_limit}]: ",
        0,
        number_of_skaters - qualification_limit,
    )

    print("\nRESTRICTION BASED ON THE CLASSIFICATION AFTER THREE DISTANCES")
    print(
        "At some international competitions, only Skaters "
        "ranked within the top X of the classification after three distances "
        "are eligible for selection for the fourth distance."
    )
    apply_overall_rank_limit = ask_yes_no(
        "Does this restriction apply to this practice case? [y/n]: "
    )

    overall_rank_limit: int | None = None
    force_outside_top_x_longest_top_y = False

    if apply_overall_rank_limit:
        minimum_rank_limit = qualification_limit
        overall_rank_limit = ask_integer(
            "Only Skaters ranked within the top "
            " of the classification after three distances are eligible. Enter X: "
            f"[{minimum_rank_limit}-{number_of_skaters}]: ",
            minimum_rank_limit,
            number_of_skaters,
        )

        if overall_rank_limit < number_of_skaters:
            print("\nINTERNATIONAL SELECTION TRAP")
            print(
                f"Generate a Skater who is OUTSIDE the top-"
                f"{overall_rank_limit} in the classification after three distances, "
                f"but IS ranked among the top {qualification_limit} in the "
                "longest distance?"
            )
            print(
                "This Skater appears eligible based on the longest-distance ranking, "
                "but is not eligible for selection because of the top-X restriction "
                "in the classification after three distances."
            )
            force_outside_top_x_longest_top_y = ask_yes_no(
                "Include this situation deliberately in the practice case? [y/n]: "
            )
        else:
            print(
                "\nLet op: de klasslimiet omvat alle deelnemers. "
                "A Skater outside the top-X can therefore not be "
                "generated."
            )

    tie_scenario = choose_tie_scenario()

    max_tie_positions = 0
    if tie_scenario != "none":
        max_tie_positions = ask_integer(
            "What is the maximum number of tied positions to generate? "
            "[1-3]: ",
            1,
            3,
        )

    seed = ask_optional_integer(
        "\nNummer van de oefencasus "
        "(zelfde nummer geeft steeds dezelfde uitslag), "
        "of druk op Enter voor een nieuwe randome casus: "
    )

    simulate_incidents = ask_yes_no(
        "\nSimulate DQ, DNS, DNF or WDR incidents? [y/n]: "
    )

    incident_count = 0
    if simulate_incidents:
        incident_count = ask_integer(
            "How many incidents should be simulated? [1-4]: ",
            1,
            4,
        )

    create_exercises = ask_yes_no(
        "Generate practice questions automatically? [y/n]: "
    )

    save_outputs = ask_yes_no(
        "Save the results as TXT and JSON as well? [y/n]: "
    )

    return TournamentConfig(
        gender=gender,
        distances=distances,
        number_of_skaters=number_of_skaters,
        qualification_limit=qualification_limit,
        reserve_count=reserve_count,
        apply_overall_rank_limit=apply_overall_rank_limit,
        overall_rank_limit=overall_rank_limit,
        force_outside_top_x_longest_top_y=(
            force_outside_top_x_longest_top_y
        ),
        tie_scenario=tie_scenario,
        max_tie_positions=max_tie_positions,
        seed=seed,
        simulate_incidents=simulate_incidents,
        incident_count=incident_count,
        create_exercises=create_exercises,
        save_outputs=save_outputs,
    )


# =============================================================================
# GENERATION
# =============================================================================

def select_names(
    gender: CompetitionGender,
    number_of_skaters: int,
    rng: random.Random,
) -> list[str]:
    available_names = (
        FICTIONAL_WOMEN_NAMES
        if gender == "women"
        else FICTIONAL_MEN_NAMES
    )

    return rng.sample(available_names, number_of_skaters)


def distance_profile_factor(distance: int) -> float:
    """
    Negatief = voordeel voor sprinters, positief = voordeel voor stayers.

    Deze factor zorgt ervoor dat de ranglijst van de in longest distance
    niet vrijwel identiek wordt aan het allroundklassement. Dat is
    didactisch belangrijk voor de selectie van de vierde afstand.
    """
    factors = {
        500: -1.00,
        1000: -0.65,
        1500: -0.25,
        3000: 0.35,
        5000: 0.75,
        10000: 1.00,
    }
    return factors.get(distance, 0.0)


def generate_time(
    distance: int,
    ability: float,
    rng: random.Random,
    gender: CompetitionGender,
) -> float:
    reference_times = REFERENCE_TIMES[gender]

    if distance not in reference_times:
        raise ValueError(
            f"Geen referentietijd ingesteld voor {distance} meter."
        )

    base_time = reference_times[distance]

    ability_effect = ability * (distance / 500) * 0.55
    variation = rng.gauss(
        0,
        0.20 * (distance / 500) ** 0.55,
    )

    return round(
        base_time + ability_effect + variation,
        2,
    )


def create_initial_skaters(
    config: TournamentConfig,
    rng: random.Random,
) -> list[Skater]:
    names = select_names(
        gender=config.gender,
        number_of_skaters=config.number_of_skaters,
        rng=rng,
    )

    skaters = [
        Skater(
            bib=51 + index,
            name=name,
            ability=max(-1.35, min(1.35, rng.gauss(0, 0.50))),
            endurance_bias=max(-0.85, min(0.85, rng.gauss(0, 0.42))),
        )
        for index, name in enumerate(names)
    ]

    for skater in skaters:
        for distance in config.distances:
            effective_ability = (
                skater.ability
                + skater.endurance_bias * distance_profile_factor(distance)
            )

            skater.times[distance] = generate_time(
                distance=distance,
                ability=effective_ability,
                rng=rng,
                gender=config.gender,
            )
            skater.statuses[distance] = "OK"

    return skaters



def has_outside_top_x_longest_top_y_trap(
    skaters: list[Skater],
    overall_rank_limit: int,
    qualification_limit: int,
) -> bool:
    """
    True als er minimaal één valid rijder is die:
    - na drie afstanden BUITEN de toegestane top-X staat; én
    - op de in longest distance WEL bij de beste Y staat,
      waarbij Y het aantal rijders voor de vierde afstand is.

    Dit is bewust een internationale selectie-valkuil: de rijder staat
    hoog genoeg op de in longest distance, maar mag vanwege de top-X-regel
    niet worden geselecteerd.
    """
    for skater in eligible_skaters_after_3(skaters):
        cr = skater.overall_rank_after_3
        lr = skater.longest_distance_rank

        if cr is None or lr is None:
            continue

        if (
            cr > overall_rank_limit
            and lr <= qualification_limit
        ):
            return True

    return False


def has_meaningful_fourth_distance_selection(
    skaters: list[Skater],
    qualification_limit: int,
    overall_rank_limit: int | None = None,
) -> bool:
    """
    Controleert of de oefencasus daadwerkelijk vraagt om het combineren
    van beide ranglijsten.

    Gewenst:
    - minimaal één rijder staat wel in top-N klassement, maar niet in
      top-N in longest distance;
    - minimaal één rijder staat wel in top-N in longest distance, maar niet
      in top-N klassement.

    Als een internationale top-X-beperking geldt, worden alleen rijders
    meegenomen die na drie afstanden binnen die top-X staan.
    """
    eligible = eligible_skaters_after_3(skaters)

    if overall_rank_limit is not None:
        eligible = [
            skater
            for skater in eligible
            if (
                skater.overall_rank_after_3 is not None
                and skater.overall_rank_after_3 <= overall_rank_limit
            )
        ]

    classification_only = [
        skater
        for skater in eligible
        if (
            skater.overall_rank_after_3 is not None
            and skater.longest_distance_rank is not None
            and skater.overall_rank_after_3 <= qualification_limit
            and skater.longest_distance_rank > qualification_limit
        )
    ]

    longest_only = [
        skater
        for skater in eligible
        if (
            skater.overall_rank_after_3 is not None
            and skater.longest_distance_rank is not None
            and skater.overall_rank_after_3 > qualification_limit
            and skater.longest_distance_rank <= qualification_limit
        )
    ]

    return bool(classification_only and longest_only)


def create_initial_skaters_with_selection_challenge(
    config: TournamentConfig,
    rng: random.Random,
    max_attempts: int = 250,
) -> list[Skater]:
    """
    Genereert bij voorkeur een veld waarin de twee selectielijsten
    daadwerkelijk van elkaar verschillen rond de top-N.

    De tijden blijven volledig uit het normale tijdmodel komen; er worden
    dus geen kunstmatige posities achteraf 'ingetekend'.
    """
    fallback: list[Skater] | None = None

    for _ in range(max_attempts):
        candidate = create_initial_skaters(config, rng)
        recalculate_all(candidate, config.distances)
        fallback = candidate

        has_selection_challenge = has_meaningful_fourth_distance_selection(
            candidate,
            config.qualification_limit,
            (
                config.overall_rank_limit
                if config.apply_overall_rank_limit
                else None
            ),
        )

        has_requested_international_trap = True
        if (
            config.apply_overall_rank_limit
            and config.force_outside_top_x_longest_top_y
            and config.overall_rank_limit is not None
        ):
            has_requested_international_trap = (
                has_outside_top_x_longest_top_y_trap(
                    candidate,
                    config.overall_rank_limit,
                    config.qualification_limit,
                )
            )

        if (
            has_selection_challenge
            and has_requested_international_trap
        ):
            return candidate

    if fallback is None:
        raise RuntimeError("Kon geen deelnemersveld genereren.")

    return fallback


def international_top_x_trap_diagnostics(
    skaters: list[Skater],
    overall_rank_limit: int | None,
    qualification_limit: int,
) -> list[str]:
    """
    Beschrijft rijders die door de internationale top-X-regel NIET
    selecteerbaar zijn, ondanks een top-Y-rank op de in longest distance.
    """
    if overall_rank_limit is None:
        return []

    messages: list[str] = []

    for skater in eligible_skaters_after_3(skaters):
        cr = skater.overall_rank_after_3
        lr = skater.longest_distance_rank

        if cr is None or lr is None:
            continue

        if (
            cr > overall_rank_limit
            and lr <= qualification_limit
        ):
            messages.append(
                f"{skater.name}: rank {cr} in het tussenklassement "
                f"(outside top-{overall_rank_limit}), maar rank {lr} "
                f"op de in longest distance (top-{qualification_limit}). "
                "Not eligible for selection because of the classification limit."
            )

    return sorted(messages)


def fourth_distance_selection_diagnostics(
    skaters: list[Skater],
    qualification_limit: int,
    overall_rank_limit: int | None = None,
) -> list[str]:
    """
    Geeft didactische informatie over rijders die slechts in één van de
    twee top-N-lijsten staan.

    Bij een internationale top-X-beperking worden rijders buiten die
    klassering expliciet buiten de selecteerbare groep gehouden.
    """
    messages: list[str] = []

    for skater in eligible_skaters_after_3(skaters):
        cr = skater.overall_rank_after_3
        lr = skater.longest_distance_rank

        if cr is None or lr is None:
            continue

        if overall_rank_limit is not None and cr > overall_rank_limit:
            continue

        if cr <= qualification_limit < lr:
            messages.append(
                f"{skater.name}: top-{qualification_limit} klassement "
                f"({cr}); not top-{qualification_limit} in longest distance ({lr})."
            )
        elif lr <= qualification_limit < cr:
            messages.append(
                f"{skater.name}: top-{qualification_limit} in longest distance "
                f"({lr}); not top-{qualification_limit} in classification ({cr})."
            )

    return sorted(messages)




# =============================================================================
# INCIDENT SIMULATION
# =============================================================================

def apply_incident_to_skater(
    skater: Skater,
    distances: list[int],
    distance_index: int,
    status: RaceStatus,
) -> str:
    """
    Past één incident toe en geeft de bijbehorende melding terug.
    """
    distance = distances[distance_index]

    if status == "DNS":
        # Bij een Allround Combination geldt: zodra een rijder op een
        # afstand DNS is, mag deze niet meer starten op de nog volgende
        # afstanden van de combinatie. Daarom verwijderen we ook alle
        # reeds gegenereerde tijden op de volgende afstanden.
        skater.statuses[distance] = "DNS"
        skater.times[distance] = None

        for later_distance in distances[distance_index + 1:]:
            # Na een DNS mag de rijder niet meer starten. In de lijsten
            # tonen we daarom alleen DNS op de afstand waarop de rijder
            # daadwerkelijk niet gestart is. De volgende afstanden worden
            # als '-' weergegeven.
            skater.statuses[later_distance] = "N/A"
            skater.times[later_distance] = None

        if distance_index < len(distances) - 1:
            following = ", ".join(
                f"{d} m" for d in distances[distance_index + 1:]
            )
            return (
                f"{skater.name} (bib {skater.bib}) does not start in the "
                f"de {distance} m: DNS. De rijder mag daarna niet meer "
                f"starten; de volgende afstanden worden als '-' weergegeven "
                f"({following})."
            )

        return (
            f"{skater.name} (bib {skater.bib}) does not start in the "
            f"de {distance} m: DNS."
        )

    if status == "DNF":
        skater.statuses[distance] = "DNF"
        skater.times[distance] = None
        return (
            f"{skater.name} (bib {skater.bib}) finisht niet op "
            f"de {distance} m: DNF."
        )

    if status == "DQ":
        skater.statuses[distance] = "DQ"
        return (
            f"{skater.name} (bib {skater.bib}) wordt "
            f"gediskwalificeerd op de {distance} m: DQ."
        )

    # WDR wordt alleen vermeld op de afstand waarvoor de rijder al
    # op de startlijst stond, maar zich daarna heeft afgemeld.
    #
    # Vanaf dat moment is de rijder niet meer startgerechtigd voor de
    # volgende afstanden. Die latere afstanden krijgen daarom intern
    # N/A en worden in de lijsten als '-' weergegeven.
    skater.statuses[distance] = "WDR"
    skater.times[distance] = None

    for later_distance in distances[distance_index + 1:]:
        skater.statuses[later_distance] = "N/A"
        skater.times[later_distance] = None

    if distance_index < len(distances) - 1:
        following = ", ".join(
            f"{d} m" for d in distances[distance_index + 1:]
        )
        return (
            f"{skater.name} (bib {skater.bib}) trekt zich terug voor "
            f"de {distance} m after having been entered on the start list: WDR. "
            f"Subsequent distances are shown as '-' "
            f"({following})."
        )

    return (
        f"{skater.name} (bib {skater.bib}) trekt zich terug voor "
        f"de {distance} m after having been entered on the start list: WDR."
    )


def simulate_incidents(
    skaters: list[Skater],
    distances: list[int],
    incident_count: int,
    rng: random.Random,
) -> tuple[list[str], list[RaceStatus]]:
    """
    Verdeelt incidenten random over alle vier afstanden.

    Incidenten op afstand 1 t/m 3 worden direct toegepast, omdat ze invloed
    hebben op de tussenklassementen en de kwalificatie voor de vierde afstand.

    Incidenten op de vierde afstand worden tijdelijk opgeslagen. Ze worden
    pas na de selectie voor de vierde afstand gekoppeld aan een daadwerkelijk
    geselecteerde rijder.
    """
    messages: list[str] = []
    pending_fourth_distance_incidents: list[RaceStatus] = []
    used: set[tuple[int, int]] = set()
    statuses: list[RaceStatus] = ["DQ", "DNS", "DNF", "WDR"]

    for _ in range(incident_count):
        distance_index = rng.randrange(0, len(distances))
        status = rng.choice(statuses)

        # De vierde afstand wordt pas na de kwalificatie verwerkt.
        if distance_index == len(distances) - 1:
            pending_fourth_distance_incidents.append(status)
            continue

        for _attempt in range(100):
            skater = rng.choice(skaters)
            distance = distances[distance_index]

            if (skater.bib, distance) in used:
                continue

            if skater.statuses[distance] != "OK":
                continue

            used.add((skater.bib, distance))
            messages.append(
                apply_incident_to_skater(
                    skater=skater,
                    distances=distances,
                    distance_index=distance_index,
                    status=status,
                )
            )
            break

    return messages, pending_fourth_distance_incidents


def apply_fourth_distance_incidents(
    selected: list[Skater],
    distances: list[int],
    pending_statuses: list[RaceStatus],
    rng: random.Random,
) -> list[str]:
    """
    Koppelt uitgestelde incidenten op de vierde afstand aan geselecteerde
    deelnemers. Exact dezelfde rijder krijgt niet twee incidenten op die
    afstand.
    """
    messages: list[str] = []

    if not pending_statuses or not selected:
        return messages

    available = selected.copy()
    rng.shuffle(available)
    fourth_index = len(distances) - 1

    for status, skater in zip(pending_statuses, available):
        if skater.statuses[distances[fourth_index]] != "OK":
            continue

        messages.append(
            apply_incident_to_skater(
                skater=skater,
                distances=distances,
                distance_index=fourth_index,
                status=status,
            )
        )

    return messages


# =============================================================================
# CALCULATION
# =============================================================================

def calculate_points(
    skaters: list[Skater],
    distances: list[int],
) -> None:
    for skater in skaters:
        for distance in distances:
            status = skater.statuses[distance]
            time = skater.times[distance]

            if status == "OK" and time is not None:
                skater.points[distance] = round(
                    points_for_distance(time, distance),
                    3,
                )
            else:
                skater.points[distance] = None


def calculate_distance_ranks(
    skaters: list[Skater],
    distances: list[int],
) -> None:
    for distance in distances:
        valid_values = [
            (skater.bib, skater.times[distance])
            for skater in skaters
            if (
                skater.statuses[distance] == "OK"
                and skater.times[distance] is not None
            )
        ]

        ranks = competition_ranks(
            [(bib, float(value)) for bib, value in valid_values],
            decimals=2,
        )

        for skater in skaters:
            skater.distance_ranks[distance] = ranks.get(skater.bib)


def calculate_intermediate_classifications(
    skaters: list[Skater],
    distances: list[int],
) -> None:
    first_two = distances[:2]
    first_three = distances[:3]

    for skater in skaters:
        skater.eligible_after_2 = all(
            skater.statuses[d] == "OK"
            and skater.points[d] is not None
            for d in first_two
        )

        skater.eligible_after_3 = all(
            skater.statuses[d] == "OK"
            and skater.points[d] is not None
            for d in first_three
        )

        skater.total_points_after_2 = (
            round(
                sum(float(skater.points[d]) for d in first_two),
                3,
            )
            if skater.eligible_after_2
            else None
        )

        skater.total_points_after_3 = (
            round(
                sum(float(skater.points[d]) for d in first_three),
                3,
            )
            if skater.eligible_after_3
            else None
        )

    valid_after_2 = [
        (skater.bib, skater.total_points_after_2)
        for skater in skaters
        if skater.total_points_after_2 is not None
    ]

    valid_after_3 = [
        (skater.bib, skater.total_points_after_3)
        for skater in skaters
        if skater.total_points_after_3 is not None
    ]

    ranks_after_2 = competition_ranks(
        [(bib, float(value)) for bib, value in valid_after_2],
        decimals=3,
    )

    ranks_after_3 = competition_ranks(
        [(bib, float(value)) for bib, value in valid_after_3],
        decimals=3,
    )

    longest_completed_distance = max(distances[:3])

    for skater in skaters:
        skater.overall_rank_after_2 = ranks_after_2.get(skater.bib)
        skater.overall_rank_after_3 = ranks_after_3.get(skater.bib)
        skater.longest_distance_rank = (
            skater.distance_ranks.get(longest_completed_distance)
        )


def recalculate_all(
    skaters: list[Skater],
    distances: list[int],
) -> None:
    calculate_points(skaters, distances)
    calculate_distance_ranks(skaters, distances)
    calculate_intermediate_classifications(skaters, distances)


# =============================================================================
# EX AEQUO SCENARIOS
# =============================================================================

def eligible_skaters_after_3(
    skaters: list[Skater],
) -> list[Skater]:
    return [
        skater
        for skater in skaters
        if skater.eligible_after_3
    ]


def force_classification_tie(
    skater_a: Skater,
    skater_b: Skater,
    distances: list[int],
) -> None:
    """
    Maakt twee rijders ECHT ex aequo na drie afstanden.

    Omdat tijden op honderdsten worden vastgelegd en het klassement op
    duizendsten punten wordt berekend, is alleen een theoretische doeltijd
    niet voldoende. Daarom zoekt deze functie binnen een kleine realistische
    bandbreedte naar twee tijden op 0,01 seconde die na puntenberekening
    exact hetzelfde (afgeronde) totaal op 0,001 punt opleveren.
    """
    third_distance = distances[2]

    if (
        skater_a.total_points_after_3 is None
        or skater_b.total_points_after_3 is None
    ):
        raise ValueError(
            "Beide rijders moeten een geldig klassement na drie "
            "distances."
        )

    current_time_a = skater_a.times[third_distance]
    current_time_b = skater_b.times[third_distance]

    if current_time_a is None or current_time_b is None:
        raise ValueError(
            "Both Skaters must have a valid time in the third distance "
            "hebben."
        )

    first_two_a = sum(
        float(skater_a.points[d])
        for d in distances[:2]
        if skater_a.points[d] is not None
    )
    first_two_b = sum(
        float(skater_b.points[d])
        for d in distances[:2]
        if skater_b.points[d] is not None
    )

    maximum_adjustment = {
        500: 0.50,
        1000: 0.90,
        1500: 1.35,
        3000: 2.25,
        5000: 3.50,
        10000: 5.50,
    }.get(third_distance, 1.35)

    midpoint_total = (
        float(skater_a.total_points_after_3)
        + float(skater_b.total_points_after_3)
    ) / 2

    def possible_times(
        current_time: float,
        first_two_points: float,
    ) -> dict[float, tuple[float, float]]:
        """
        Geeft per bereikbaar totaal de beste tijd terug:
        {totaalpunten: (tijd, afwijking_van_oorspronkelijke_tijd)}
        """
        result: dict[float, tuple[float, float]] = {}

        start_hundredths = int(
            round((current_time - maximum_adjustment) * 100)
        )
        end_hundredths = int(
            round((current_time + maximum_adjustment) * 100)
        )

        for hundredths in range(start_hundredths, end_hundredths + 1):
            candidate_time = hundredths / 100

            if candidate_time <= 0:
                continue

            candidate_points = round(
                points_for_distance(candidate_time, third_distance),
                3,
            )
            total = round(first_two_points + candidate_points, 3)
            adjustment = abs(candidate_time - current_time)

            previous = result.get(total)
            if previous is None or adjustment < previous[1]:
                result[total] = (candidate_time, adjustment)

        return result

    options_a = possible_times(float(current_time_a), first_two_a)
    options_b = possible_times(float(current_time_b), first_two_b)

    shared_totals = set(options_a) & set(options_b)

    if not shared_totals:
        raise ValueError(
            "Deze combinatie van rijders kan binnen een realistische "
            "tijdcorrectie niet exact ex aequo worden gemaakt."
        )

    best_total = min(
        shared_totals,
        key=lambda total: (
            abs(total - midpoint_total),
            max(options_a[total][1], options_b[total][1]),
            options_a[total][1] + options_b[total][1],
        ),
    )

    required_time_a = options_a[best_total][0]
    required_time_b = options_b[best_total][0]

    skater_a.statuses[third_distance] = "OK"
    skater_b.statuses[third_distance] = "OK"
    skater_a.times[third_distance] = required_time_a
    skater_b.times[third_distance] = required_time_b


def force_race_result_tie(
    skater_a: Skater,
    skater_b: Skater,
    distance: int,
) -> None:
    if skater_a.times[distance] is None:
        raise ValueError(
            "Skater A has no valid time for the tie."
        )

    skater_b.statuses[distance] = "OK"
    skater_b.times[distance] = skater_a.times[distance]


def select_closest_classification_pair(
    skaters: list[Skater],
    distances: list[int],
    preferred_rank: int | None = None,
) -> tuple[Skater, Skater]:
    """
    Selecteert twee rijders die qua puntentotaal dicht bij elkaar staan
    en met een beperkte tijdcorrectie ex aequo gemaakt kunnen worden.
    """
    eligible = sorted(
        eligible_skaters_after_3(skaters),
        key=lambda skater: (
            skater.total_points_after_3
            if skater.total_points_after_3 is not None
            else float("inf"),
            skater.bib,
        ),
    )

    if len(eligible) < 2:
        raise ValueError("Niet genoeg valid rijders voor een ex aequo.")

    candidates: list[tuple[float, float, Skater, Skater]] = []
    third_distance = distances[2]

    maximum_adjustment = {
        500: 0.40,
        1000: 0.80,
        1500: 1.20,
        3000: 2.00,
        5000: 3.00,
        10000: 5.00,
    }.get(third_distance, 1.20)

    for skater_a, skater_b in zip(eligible, eligible[1:]):
        if (
            skater_a.total_points_after_3 is None
            or skater_b.total_points_after_3 is None
            or skater_a.times[third_distance] is None
            or skater_b.times[third_distance] is None
        ):
            continue

        target_points = (
            skater_a.total_points_after_3
            + skater_b.total_points_after_3
        ) / 2

        first_two_a = sum(
            float(skater_a.points[d])
            for d in distances[:2]
            if skater_a.points[d] is not None
        )
        first_two_b = sum(
            float(skater_b.points[d])
            for d in distances[:2]
            if skater_b.points[d] is not None
        )

        required_a = (
            target_points - first_two_a
        ) * third_distance / 500
        required_b = (
            target_points - first_two_b
        ) * third_distance / 500

        max_change = max(
            abs(required_a - float(skater_a.times[third_distance])),
            abs(required_b - float(skater_b.times[third_distance])),
        )

        if max_change > maximum_adjustment:
            continue

        rank_distance = 0.0
        if preferred_rank is not None:
            pair_rank = min(
                skater_a.overall_rank_after_3 or 999,
                skater_b.overall_rank_after_3 or 999,
            )
            rank_distance = abs(pair_rank - preferred_rank)

        points_difference = abs(
            skater_a.total_points_after_3
            - skater_b.total_points_after_3
        )

        candidates.append(
            (
                rank_distance,
                points_difference,
                skater_a,
                skater_b,
            )
        )

    if not candidates:
        raise ValueError(
            "Geen realistisch paar gevonden voor een klassementsex-aequo."
        )

    candidates.sort(key=lambda item: (item[0], item[1]))
    _, _, skater_a, skater_b = candidates[0]
    return skater_a, skater_b


def pair_bibs(pair: tuple[Skater, Skater]) -> set[int]:
    return {pair[0].bib, pair[1].bib}


def pair_is_allowed(
    pair: tuple[Skater, Skater],
    used_pairs: list[tuple[Skater, Skater]],
    forbidden_exact_pair: tuple[Skater, Skater] | None = None,
) -> bool:
    """
    Staat nieuwe paren toe zolang:
    - exact hetzelfde paar niet opnieuw wordt gebruikt;
    - bij een verboden paar niet beide rijders opnieuw samen voorkomen.

    Eén rijder mag dus terugkomen in een ander ex-aequopaar.
    """
    new_bibs = pair_bibs(pair)

    for used_pair in used_pairs:
        # Een rijder mag niet in twee verschillende geforceerde ex-aequo's
        # voorkomen. Anders kan een latere correctie een eerder ex aequo
        # weer ongedaan maken.
        if new_bibs & pair_bibs(used_pair):
            return False

    if forbidden_exact_pair is not None:
        if new_bibs == pair_bibs(forbidden_exact_pair):
            return False

    return True


def select_multiple_classification_pairs(
    skaters: list[Skater],
    distances: list[int],
    count: int,
    rng: random.Random,
    preferred_rank: int | None = None,
    preferred_top_n: int | None = None,
) -> list[tuple[Skater, Skater]]:
    """
    Selecteert maximaal 'count' realistische, verschillende paren voor
    ex aequo in het tussenklassement.
    """
    eligible = sorted(
        eligible_skaters_after_3(skaters),
        key=lambda skater: (
            skater.total_points_after_3
            if skater.total_points_after_3 is not None
            else float("inf"),
            skater.bib,
        ),
    )

    candidates: list[tuple[float, float, Skater, Skater]] = []
    third_distance = distances[2]

    maximum_adjustment = {
        500: 0.40,
        1000: 0.80,
        1500: 1.20,
        3000: 2.00,
        5000: 3.00,
        10000: 5.00,
    }.get(third_distance, 1.20)

    # Alleen nabijgelegen rijders vergelijken; dat houdt de tijden realistisch.
    for i in range(len(eligible)):
        for j in range(i + 1, min(i + 4, len(eligible))):
            skater_a = eligible[i]
            skater_b = eligible[j]

            if (
                skater_a.total_points_after_3 is None
                or skater_b.total_points_after_3 is None
                or skater_a.times[third_distance] is None
                or skater_b.times[third_distance] is None
            ):
                continue

            target_points = (
                skater_a.total_points_after_3
                + skater_b.total_points_after_3
            ) / 2

            first_two_a = sum(
                float(skater_a.points[d])
                for d in distances[:2]
                if skater_a.points[d] is not None
            )
            first_two_b = sum(
                float(skater_b.points[d])
                for d in distances[:2]
                if skater_b.points[d] is not None
            )

            required_a = (
                target_points - first_two_a
            ) * third_distance / 500
            required_b = (
                target_points - first_two_b
            ) * third_distance / 500

            max_change = max(
                abs(required_a - float(skater_a.times[third_distance])),
                abs(required_b - float(skater_b.times[third_distance])),
            )

            if max_change > maximum_adjustment:
                continue

            pair_rank_a = skater_a.overall_rank_after_3 or 999
            pair_rank_b = skater_b.overall_rank_after_3 or 999

            # Geforceerde ex-aequo's horen bij voorkeur in het relevante
            # bovenste deel van de lijst: de rijders die voor selectie in
            # aanmerking komen. Alleen als daar geen realistisch paar
            # beschikbaar is, vallen we terug op de rest van de lijst.
            if preferred_top_n is not None:
                if not (
                    pair_rank_a <= preferred_top_n
                    and pair_rank_b <= preferred_top_n
                ):
                    continue

            top_n_penalty = 0.0
            rank_distance = 0.0
            if preferred_rank is not None:
                pair_rank = min(pair_rank_a, pair_rank_b)
                rank_distance = abs(pair_rank - preferred_rank)

            points_difference = abs(
                skater_a.total_points_after_3
                - skater_b.total_points_after_3
            )

            # Kleine random factor voorkomt dat dezelfde structuur steeds terugkomt.
            candidates.append(
                (
                    top_n_penalty + rank_distance,
                    points_difference + rng.random() * 0.0001,
                    skater_a,
                    skater_b,
                )
            )

    candidates.sort(key=lambda item: (item[0], item[1]))

    selected: list[tuple[Skater, Skater]] = []

    for _, _, skater_a, skater_b in candidates:
        pair = (skater_a, skater_b)

        if pair_is_allowed(pair, selected):
            selected.append(pair)

        if len(selected) >= count:
            break

    return selected


def select_multiple_race_pairs(
    skaters: list[Skater],
    distance: int,
    count: int,
    rng: random.Random,
    forbidden_pairs: list[tuple[Skater, Skater]] | None = None,
    preferred_top_n: int | None = None,
) -> list[tuple[Skater, Skater]]:
    """
    Selecteert maximaal 'count' verschillende ex-aequoparen voor de
    in longest distance.

    Een rijder mag ook in een klassementsex-aequo voorkomen, maar exact
    hetzelfde tweetal wordt vermeden.
    """
    forbidden_pairs = forbidden_pairs or []

    eligible = sorted(
        [
            skater
            for skater in eligible_skaters_after_3(skaters)
            if skater.times[distance] is not None
        ],
        key=lambda skater: (
            float(skater.times[distance]),
            skater.bib,
        ),
    )

    candidates: list[tuple[float, float, Skater, Skater]] = []

    for i in range(len(eligible)):
        for j in range(i + 1, min(i + 4, len(eligible))):
            skater_a = eligible[i]
            skater_b = eligible[j]
            difference = abs(
                float(skater_a.times[distance])
                - float(skater_b.times[distance])
            )

            rank_a = skater_a.distance_ranks.get(distance) or 999
            rank_b = skater_b.distance_ranks.get(distance) or 999

            if preferred_top_n is not None:
                if not (
                    rank_a <= preferred_top_n
                    and rank_b <= preferred_top_n
                ):
                    continue

            top_n_penalty = 0.0
            candidates.append(
                (
                    top_n_penalty + difference,
                    rng.random(),
                    skater_a,
                    skater_b,
                )
            )

    candidates.sort(key=lambda item: (item[0], item[1]))

    selected: list[tuple[Skater, Skater]] = []

    for _, _, skater_a, skater_b in candidates:
        pair = (skater_a, skater_b)

        if not pair_is_allowed(pair, selected):
            continue

        # Gebruik geen rijder die al onderdeel is van een geforceerd
        # klassementsex-aequo. Anders kan het aanpassen van de langste
        # afstand dat eerdere klassementsex-aequo weer verbreken.
        if any(pair_bibs(pair) & pair_bibs(fp) for fp in forbidden_pairs):
            continue

        selected.append(pair)

        if len(selected) >= count:
            break

    return selected


def select_closest_race_pair(
    skaters: list[Skater],
    distance: int,
) -> tuple[Skater, Skater]:
    """
    Selecteert twee rijders met vrijwel gelijke tijden op een afstand.
    """
    eligible = sorted(
        [
            skater
            for skater in eligible_skaters_after_3(skaters)
            if skater.times[distance] is not None
        ],
        key=lambda skater: (
            float(skater.times[distance]),
            skater.bib,
        ),
    )

    if len(eligible) < 2:
        raise ValueError(
            "Niet genoeg valid rijders voor een ex aequo in de uitslag."
        )

    return min(
        zip(eligible, eligible[1:]),
        key=lambda pair: abs(
            float(pair[0].times[distance])
            - float(pair[1].times[distance])
        ),
    )


def select_skaters_near_boundary(
    skaters: list[Skater],
    boundary: int,
) -> tuple[Skater, Skater]:
    eligible = sorted(
        eligible_skaters_after_3(skaters),
        key=lambda skater: (
            skater.overall_rank_after_3
            if skater.overall_rank_after_3 is not None
            else 999,
            skater.total_points_after_3
            if skater.total_points_after_3 is not None
            else float("inf"),
            skater.bib,
        ),
    )

    if len(eligible) < 2:
        raise ValueError(
            "Niet genoeg valid rijders voor een ex aequo rond de grens."
        )

    index_a = max(
        0,
        min(boundary - 1, len(eligible) - 2),
    )

    return eligible[index_a], eligible[index_a + 1]


def apply_tie_scenario(
    skaters: list[Skater],
    config: TournamentConfig,
    rng: random.Random,
) -> list[str]:
    messages: list[str] = []

    if config.tie_scenario == "none":
        return messages

    eligible = eligible_skaters_after_3(skaters)

    if len(eligible) < 2:
        messages.append(
            "Ex-aequoscenario kon niet worden toegepast: "
            "too few eligible Skaters."
        )
        return messages

    longest_completed_distance = max(config.distances[:3])

    # Het gekozen aantal is een maximum. We forceren liever minder
    # relevante ex-aequo's in de top-N dan extra ex-aequo's onderaan.
    requested_count = rng.randint(1, max(1, config.max_tie_positions))

    successful_classification_pairs: list[tuple[Skater, Skater]] = []
    successful_race_pairs: list[tuple[Skater, Skater]] = []

    if config.tie_scenario in {
        "classification",
        "both",
        "qualification_boundary",
    }:
        preferred_rank = (
            max(1, config.qualification_limit - 2)
            if config.tie_scenario == "qualification_boundary"
            else None
        )

        # Meer kandidaten ophalen dan strikt nodig, zodat een kandidaat
        # die door honderdsten/duizendsten niet exact maakbaar blijkt
        # netjes kan worden overgeslagen.
        candidate_pairs = select_multiple_classification_pairs(
            skaters=skaters,
            distances=config.distances,
            count=max(requested_count * 4, requested_count),
            rng=rng,
            preferred_rank=preferred_rank,
            preferred_top_n=config.qualification_limit,
        )

        for skater_a, skater_b in candidate_pairs:
            if len(successful_classification_pairs) >= requested_count:
                break

            if any(
                pair_bibs((skater_a, skater_b)) & pair_bibs(pair)
                for pair in successful_classification_pairs
            ):
                continue

            try:
                force_classification_tie(
                    skater_a,
                    skater_b,
                    config.distances,
                )
                recalculate_all(skaters, config.distances)

                # Alleen melden als het ex aequo na herberekening echt bestaat.
                if (
                    skater_a.total_points_after_3 is not None
                    and skater_b.total_points_after_3 is not None
                    and round(skater_a.total_points_after_3, 3)
                    == round(skater_b.total_points_after_3, 3)
                ):
                    successful_classification_pairs.append(
                        (skater_a, skater_b)
                    )
                    messages.append(
                        f"Tie in the classification after three distances: "
                        f"{skater_a.name} en {skater_b.name} "
                        f"(rank {skater_a.overall_rank_after_3})."
                    )
            except ValueError:
                continue

    if config.tie_scenario in {
        "longest_distance",
        "both",
        "qualification_boundary",
    }:
        candidate_pairs = select_multiple_race_pairs(
            skaters=skaters,
            distance=longest_completed_distance,
            count=max(requested_count * 4, requested_count),
            rng=rng,
            forbidden_pairs=successful_classification_pairs,
            preferred_top_n=config.qualification_limit,
        )

        for skater_a, skater_b in candidate_pairs:
            if len(successful_race_pairs) >= requested_count:
                break

            if any(
                pair_bibs((skater_a, skater_b)) & pair_bibs(pair)
                for pair in successful_race_pairs
            ):
                continue

            time_a = skater_a.times[longest_completed_distance]
            time_b = skater_b.times[longest_completed_distance]

            if time_a is None or time_b is None:
                continue

            shared_time = round((time_a + time_b) / 2, 2)

            skater_a.statuses[longest_completed_distance] = "OK"
            skater_b.statuses[longest_completed_distance] = "OK"
            skater_a.times[longest_completed_distance] = shared_time
            skater_b.times[longest_completed_distance] = shared_time

            recalculate_all(skaters, config.distances)

            if (
                skater_a.distance_ranks.get(longest_completed_distance)
                == skater_b.distance_ranks.get(longest_completed_distance)
                and skater_a.distance_ranks.get(longest_completed_distance)
                is not None
            ):
                successful_race_pairs.append((skater_a, skater_b))
                messages.append(
                    f"Tie in the {longest_completed_distance} m: "
                    f"{skater_a.name} en {skater_b.name} "
                    f"(rank "
                    f"{skater_a.distance_ranks[longest_completed_distance]})."
                )

    if not messages:
        messages.append(
            "Binnen de top van de relevante ranglijsten kon in deze casus "
            "no realistic forced tie could be generated."
        )

    return messages


# =============================================================================
# FOURTH-DISTANCE INPUT AND SIMPLE SELECTION
# =============================================================================

def make_existing_script_input(
    skaters: list[Skater],
) -> list[tuple[int, int, str, int]]:
    result: list[tuple[int, int, str, int]] = []

    for skater in sorted(
        eligible_skaters_after_3(skaters),
        key=lambda skater: (
            skater.overall_rank_after_3
            if skater.overall_rank_after_3 is not None
            else 999,
            skater.longest_distance_rank
            if skater.longest_distance_rank is not None
            else 999,
            skater.bib,
        ),
    ):
        if (
            skater.overall_rank_after_3 is not None
            and skater.longest_distance_rank is not None
        ):
            result.append(
                (
                    skater.overall_rank_after_3,
                    skater.bib,
                    skater.name,
                    skater.longest_distance_rank,
                )
            )

    return result


def select_for_fourth_distance(
    skaters: list[Skater],
    qualification_limit: int,
    reserve_count: int,
    overall_rank_limit: int | None = None,
) -> tuple[list[Skater], list[Skater]]:
    """
    Selectie voor de vierde afstand op basis van:
    - klassement in classification after three distances only;
    - uitslag langste verreden afstand;
    - directe plaatsing als rijder in beide top-N staat;
    - daarna aanvullen op de beste rank in één van beide lijsten.

    Internationale optie:
    als overall_rank_limit is ingesteld, mogen uitsluitend rijders
    geselecteerd worden die na drie afstanden binnen die top-X van het
    are eligible for selection for the fourth distance. Dezelfde beperking geldt voor de reserves.

    Dit volgt dezelfde werkwijze als het aangeleverde internationale
    vierde-afstandscript: eerst de toegestane groep filteren op de
    klassering na drie afstanden, daarna de normale selectieprocedure
    uitvoeren.
    """
    eligible = eligible_skaters_after_3(skaters)

    if overall_rank_limit is not None:
        eligible = [
            skater
            for skater in eligible
            if (
                skater.overall_rank_after_3 is not None
                and skater.overall_rank_after_3 <= overall_rank_limit
            )
        ]

    directly_qualified = [
        skater
        for skater in eligible
        if (
            skater.overall_rank_after_3 is not None
            and skater.longest_distance_rank is not None
            and skater.overall_rank_after_3 <= qualification_limit
            and skater.longest_distance_rank <= qualification_limit
        )
    ]

    selected = sorted(
        directly_qualified,
        key=lambda skater: (
            skater.overall_rank_after_3
            if skater.overall_rank_after_3 is not None
            else 999,
            skater.longest_distance_rank
            if skater.longest_distance_rank is not None
            else 999,
            skater.bib,
        ),
    )

    remaining = [
        skater
        for skater in eligible
        if skater not in selected
    ]

    # Beste rank in één van beide lijsten is leidend.
    # Bij gelijke beste positie:
    # 1. beste rank in het tussenklassement;
    # 2. daarna de rank op de in longest distance.
    remaining.sort(
        key=lambda skater: (
            min(
                skater.overall_rank_after_3
                if skater.overall_rank_after_3 is not None
                else 999,
                skater.longest_distance_rank
                if skater.longest_distance_rank is not None
                else 999,
            ),
            skater.overall_rank_after_3
            if skater.overall_rank_after_3 is not None
            else 999,
            skater.longest_distance_rank
            if skater.longest_distance_rank is not None
            else 999,
            skater.bib,
        )
    )

    for skater in remaining:
        if len(selected) >= qualification_limit:
            break
        selected.append(skater)

    reserves = [
        skater
        for skater in remaining
        if skater not in selected
    ][:reserve_count]

    return selected, reserves




# =============================================================================
# MANUAL RESULT EDITING
# =============================================================================

def find_skater_by_bib(
    skaters: list[Skater],
    bib: int,
) -> Skater:
    for skater in skaters:
        if skater.bib == bib:
            return skater

    raise ValueError(f"Geen rijder gevonden met bib {bib}.")


def show_available_skaters(
    skaters: list[Skater],
) -> None:
    print("\nAVAILABLE SKATERS")
    print("-" * 60)

    for skater in sorted(skaters, key=lambda item: item.bib):
        print(f"{skater.bib}: {skater.name}")


def choose_two_skaters(
    skaters: list[Skater],
) -> tuple[Skater, Skater]:
    show_available_skaters(skaters)

    while True:
        bib_a = ask_integer(
            "\nBib van de eerste rijder: ",
            min(skater.bib for skater in skaters),
            max(skater.bib for skater in skaters),
        )
        bib_b = ask_integer(
            "Bib van de tweede rijder: ",
            min(skater.bib for skater in skaters),
            max(skater.bib for skater in skaters),
        )

        if bib_a == bib_b:
            print("Select two different Skaters.")
            continue

        try:
            return (
                find_skater_by_bib(skaters, bib_a),
                find_skater_by_bib(skaters, bib_b),
            )
        except ValueError as error:
            print(error)


def force_classification_tie_after_2(
    skater_a: Skater,
    skater_b: Skater,
    distances: list[int],
) -> None:
    """
    Maakt twee rijders ex aequo na twee afstanden.

    De tijd op de tweede afstand van beide rijders wordt beperkt aangepast
    richting het gemiddelde van hun bestaande puntentotalen.
    """
    second_distance = distances[1]

    if (
        skater_a.total_points_after_2 is None
        or skater_b.total_points_after_2 is None
    ):
        raise ValueError(
            "Beide rijders moeten een geldig klassement na twee distances."
        )

    current_time_a = skater_a.times[second_distance]
    current_time_b = skater_b.times[second_distance]

    if current_time_a is None or current_time_b is None:
        raise ValueError(
            "Beide rijders moeten een valid tijd op de tweede afstand hebben."
        )

    target_points = round(
        (
            skater_a.total_points_after_2
            + skater_b.total_points_after_2
        ) / 2,
        3,
    )

    first_points_a = skater_a.points[distances[0]]
    first_points_b = skater_b.points[distances[0]]

    if first_points_a is None or first_points_b is None:
        raise ValueError(
            "Beide rijders moeten een valid eerste afstand hebben."
        )

    required_time_a = round(
        (target_points - float(first_points_a))
        * second_distance
        / 500,
        2,
    )
    required_time_b = round(
        (target_points - float(first_points_b))
        * second_distance
        / 500,
        2,
    )

    maximum_adjustment = {
        500: 0.40,
        1000: 0.80,
        1500: 1.20,
        3000: 2.50,
        5000: 4.00,
        10000: 7.00,
    }.get(second_distance, 2.00)

    if (
        required_time_a <= 0
        or required_time_b <= 0
        or abs(required_time_a - current_time_a) > maximum_adjustment
        or abs(required_time_b - current_time_b) > maximum_adjustment
    ):
        raise ValueError(
            "Deze twee rijders kunnen niet realistisch ex aequo worden gemaakt "
            "na twee afstanden. Kies twee rijders die dichter bij elkaar staan."
        )

    skater_a.statuses[second_distance] = "OK"
    skater_b.statuses[second_distance] = "OK"
    skater_a.times[second_distance] = required_time_a
    skater_b.times[second_distance] = required_time_b


def force_manual_race_tie(
    skater_a: Skater,
    skater_b: Skater,
    distance: int,
) -> None:
    time_a = skater_a.times[distance]
    time_b = skater_b.times[distance]

    if time_a is None or time_b is None:
        raise ValueError(
            "Both Skaters must have a valid time in this distance."
        )

    shared_time = round((time_a + time_b) / 2, 2)

    skater_a.statuses[distance] = "OK"
    skater_b.statuses[distance] = "OK"
    skater_a.times[distance] = shared_time
    skater_b.times[distance] = shared_time


def move_skater_to_distance_position(
    skaters: list[Skater],
    skater: Skater,
    distance: int,
    target_position: int,
) -> float:
    """
    Wijzigt de tijd van één rijder zodat die een unieke gewenste positie
    krijgt in de uitslag van een afstand.

    De nieuwe tijd wordt in honderdsten van seconden bepaald:
    - rank 1: één honderdste sneller dan de huidige nummer 1;
    - tussen twee rijders: een vrije honderdste tussen beide tijden;
    - laatste positie: één honderdste langzamer dan de huidige laatste.

    De gekozen rijder wordt eerst uit de bestaande rangschikking verwijderd.
    Daardoor betekent rank 5: vijfde plaats na opnieuw invoegen.
    """
    if distance not in skater.times:
        raise ValueError("Deze afstand hoort niet bij de wedstrijd.")

    other_valid_skaters = [
        other
        for other in skaters
        if (
            other.bib != skater.bib
            and other.statuses.get(distance) == "OK"
            and other.times.get(distance) is not None
        )
    ]

    if not other_valid_skaters:
        if target_position != 1:
            raise ValueError(
                "Er zijn geen andere valid tijden; alleen rank 1 is mogelijk."
            )

        current_time = skater.times.get(distance)
        new_time = float(current_time) if current_time is not None else 1.00
        skater.statuses[distance] = "OK"
        skater.times[distance] = round(new_time, 2)
        return round(new_time, 2)

    maximum_position = len(other_valid_skaters) + 1

    if not 1 <= target_position <= maximum_position:
        raise ValueError(
            f"Kies een rank tussen 1 en {maximum_position}."
        )

    sorted_centiseconds = sorted(
        int(round(float(other.times[distance]) * 100))
        for other in other_valid_skaters
        if other.times[distance] is not None
    )

    if target_position == 1:
        new_centiseconds = sorted_centiseconds[0] - 1

    elif target_position == maximum_position:
        new_centiseconds = sorted_centiseconds[-1] + 1

    else:
        faster_time = sorted_centiseconds[target_position - 2]
        slower_time = sorted_centiseconds[target_position - 1]

        if slower_time - faster_time >= 2:
            new_centiseconds = faster_time + (
                (slower_time - faster_time) // 2
            )
        else:
            threshold = slower_time

            affected = sorted(
                [
                    other
                    for other in other_valid_skaters
                    if int(round(float(other.times[distance]) * 100)) >= threshold
                ],
                key=lambda other: float(other.times[distance]),
                reverse=True,
            )

            for other in affected:
                old_centiseconds = int(
                    round(float(other.times[distance]) * 100)
                )
                other.times[distance] = (old_centiseconds + 1) / 100

            new_centiseconds = faster_time + 1

    if new_centiseconds <= 0:
        raise ValueError("De berekende tijd is niet geldig.")

    skater.statuses[distance] = "OK"
    skater.times[distance] = new_centiseconds / 100

    return new_centiseconds / 100


def print_complete_overview(
    skaters: list[Skater],
    config: TournamentConfig,
) -> tuple[list[Skater], list[Skater]]:
    """
    Herberekent en toont opnieuw alle uitslagen en klassementen.
    """
    recalculate_all(skaters, config.distances)

    selected, reserves = select_for_fourth_distance(
        skaters=skaters,
        qualification_limit=config.qualification_limit,
        reserve_count=config.reserve_count,
        overall_rank_limit=(
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
    )

    print_distance_results(
        skaters=skaters,
        distances=config.distances,
    )

    print_intermediate_classification(
        skaters=skaters,
        distances=config.distances,
        number_of_distances=2,
    )

    print_intermediate_classification(
        skaters=skaters,
        distances=config.distances,
        number_of_distances=3,
    )

    print_overall_rank_limit_exclusions(
        skaters=skaters,
        overall_rank_limit=(
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
    )

    print_fourth_distance_selection(
        selected=selected,
        reserves=reserves,
    )

    print_script_input(
        make_existing_script_input(skaters)
    )

    return selected, reserves


def manual_edit_menu(
    skaters: list[Skater],
    config: TournamentConfig,
) -> None:
    """
    Laat de gebruiker na generatie wijzigingen aanbrengen en maakt daarna
    steeds automatisch een volledig nieuw overzicht.
    """
    while True:
        print("\n" + "=" * 92)
        print("UITSLAGEN HANDMATIG AANPASSEN")
        print("=" * 92)
        print("1. Add a tie in the classification after two distances")
        print("2. Add a tie in the classification after three distances")
        print("3. Add a tie in the longest completed distance")
        print("4. Een individuele tijd handmatig wijzigen")
        print("5. Een status wijzigen: OK / DNS / DNF / DQ / WDR")
        print("6. Change a Skater’s rank in a distance")
        print("7. Volledig overzicht opnieuw tonen")
        print("0. Finish editing met aanpassen")

        choice = ask_choice(
            "Maak een keuze [0-7]: ",
            {"0", "1", "2", "3", "4", "5", "6", "7"},
        )

        if choice == "0":
            return

        try:
            if choice == "1":
                skater_a, skater_b = choose_two_skaters(skaters)
                force_classification_tie_after_2(
                    skater_a,
                    skater_b,
                    config.distances,
                )

            elif choice == "2":
                skater_a, skater_b = choose_two_skaters(skaters)
                force_classification_tie(
                    skater_a,
                    skater_b,
                    config.distances,
                )

            elif choice == "3":
                skater_a, skater_b = choose_two_skaters(skaters)
                longest_distance = max(config.distances[:3])
                force_manual_race_tie(
                    skater_a,
                    skater_b,
                    longest_distance,
                )

            elif choice == "4":
                show_available_skaters(skaters)
                bib = ask_integer(
                    "Bib van de rijder: ",
                    min(skater.bib for skater in skaters),
                    max(skater.bib for skater in skaters),
                )
                skater = find_skater_by_bib(skaters, bib)

                print(
                    "Distanceen: "
                    + ", ".join(str(distance) for distance in config.distances)
                )
                distance = ask_integer(
                    "Distance die je wilt wijzigen: ",
                    min(config.distances),
                    max(config.distances),
                )

                if distance not in config.distances:
                    raise ValueError("Deze afstand hoort niet bij de wedstrijd.")

                raw_time = input(
                    "New time in seconden, bijvoorbeeld 117.42: "
                ).strip()

                try:
                    new_time = float(raw_time)
                except ValueError as error:
                    raise ValueError("Voer een valid tijd in seconden in.") from error

                if new_time <= 0:
                    raise ValueError("De tijd moet groter zijn dan nul.")

                skater.statuses[distance] = "OK"
                skater.times[distance] = round(new_time, 2)

            elif choice == "5":
                show_available_skaters(skaters)
                bib = ask_integer(
                    "Bib van de rijder: ",
                    min(skater.bib for skater in skaters),
                    max(skater.bib for skater in skaters),
                )
                skater = find_skater_by_bib(skaters, bib)

                print(
                    "Distanceen: "
                    + ", ".join(str(distance) for distance in config.distances)
                )
                distance = ask_integer(
                    "Distance waarop je de status wilt wijzigen: ",
                    min(config.distances),
                    max(config.distances),
                )

                if distance not in config.distances:
                    raise ValueError("Deze afstand hoort niet bij de wedstrijd.")

                status_choice = ask_choice(
                    "Nieuwe status [OK/DNS/DNF/DQ/WDR]: ",
                    {"ok", "dns", "dnf", "dq", "wdr"},
                ).upper()

                skater.statuses[distance] = status_choice  # type: ignore[assignment]

                if status_choice in {"DNS", "DNF", "WDR"}:
                    skater.times[distance] = None

                if status_choice == "OK" and skater.times[distance] is None:
                    raise ValueError(
                        "First enter a valid time using option 4."
                    )

            elif choice == "6":
                show_available_skaters(skaters)

                bib = ask_integer(
                    "Bib van de rijder: ",
                    min(skater.bib for skater in skaters),
                    max(skater.bib for skater in skaters),
                )
                skater = find_skater_by_bib(skaters, bib)

                print(
                    "Distanceen: "
                    + ", ".join(str(distance) for distance in config.distances)
                )
                distance = ask_integer(
                    "Distance waarop je de rank wilt wijzigen: ",
                    min(config.distances),
                    max(config.distances),
                )

                if distance not in config.distances:
                    raise ValueError("Deze afstand hoort niet bij de wedstrijd.")

                valid_others = [
                    other
                    for other in skaters
                    if (
                        other.bib != skater.bib
                        and other.statuses.get(distance) == "OK"
                        and other.times.get(distance) is not None
                    )
                ]
                maximum_position = len(valid_others) + 1

                target_position = ask_integer(
                    f"Nieuwe rank [1-{maximum_position}]: ",
                    1,
                    maximum_position,
                )

                new_time = move_skater_to_distance_position(
                    skaters=skaters,
                    skater=skater,
                    distance=distance,
                    target_position=target_position,
                )

                print(
                    f"{skater.name} is op de {distance} m naar rank "
                    f"{target_position} verplaatst met tijd "
                    f"{format_time(new_time)}."
                )

            elif choice == "7":
                pass

            print("\nAANPASSING VERWERKT — NIEUW TOTAALOVERZICHT")
            print("=" * 92)
            print_complete_overview(
                skaters=skaters,
                config=config,
            )

        except ValueError as error:
            print(f"\nEdit not applied: {error}")


# =============================================================================
# OUTPUT
# =============================================================================

def classification_sort_key(
    skater: Skater,
    number_of_distances: int,
) -> tuple:
    """
    Sort the classification in the ISU-style order used for these
    Allround Combination practice cases.

    Classified Skaters are listed first in their official classification.

    Skaters without a classification are then ordered by:
    1. number of completed distances (most completed first);
    2. total points from the completed distances only
       (lowest hidden point total first);
    3. if those point totals are equal, status priority:
       DNF before DQ before WDR before DNS;
    4. bib number only as a final deterministic fallback.

    The point total used for unclassified Skaters is a sorting value only
    and is not displayed in the classification.
    """
    if number_of_distances == 2:
        rank = skater.overall_rank_after_2
        official_points = skater.total_points_after_2
        eligible = skater.eligible_after_2
    else:
        rank = skater.overall_rank_after_3
        official_points = skater.total_points_after_3
        eligible = skater.eligible_after_3

    # Officially classified Skaters always come first.
    if eligible:
        return (
            0,
            rank if rank is not None else 999,
            official_points if official_points is not None else float("inf"),
            skater.bib,
        )

    considered_distances = list(skater.times.keys())[:number_of_distances]

    completed_count = sum(
        1
        for distance in considered_distances
        if (
            skater.statuses.get(distance) == "OK"
            and skater.points.get(distance) is not None
        )
    )

    hidden_points = round(
        sum(
            float(skater.points[distance])
            for distance in considered_distances
            if (
                skater.statuses.get(distance) == "OK"
                and skater.points.get(distance) is not None
            )
        ),
        3,
    )

    # Only actual non-completion statuses are relevant here. "N/A" is
    # merely an internal display state for later distances after DNS/WDR.
    status_priority = {
        "DNF": 0,
        "DQ": 1,
        "WDR": 2,
        "DNS": 3,
    }

    relevant_statuses = [
        skater.statuses.get(distance)
        for distance in considered_distances
        if skater.statuses.get(distance) in status_priority
    ]

    best_status_priority = min(
        (status_priority[status] for status in relevant_statuses),
        default=99,
    )

    return (
        1,
        -completed_count,
        hidden_points,
        best_status_priority,
        skater.bib,
    )


def format_time_with_rank(
    skater: Skater,
    distance: int,
) -> str:
    status = skater.statuses[distance]

    if status == "N/A":
        return "-"

    if status != "OK":
        return status

    time = format_time(skater.times[distance])
    rank = skater.distance_ranks.get(distance)

    return f"{time} ({rank})" if rank is not None else time


def print_competition_header(config: TournamentConfig) -> None:
    gender_label = "Women" if config.gender == "women" else "Men"

    scenario_labels = {
        "none": "no forced tie",
        "classification": "tie in classification after three distances",
        "longest_distance": "tie in result of longest distance",
        "both": "tie in both rankings",
        "qualification_boundary": (
            "tie around the selection cut-off"
        ),
    }

    print("\n" + "=" * 92)
    print("GENERATED ALLROUND COMBINATION")
    print("=" * 92)
    print(f"CATEGORY:             {gender_label}")
    print(
        "DISTANCES:             "
        + " - ".join(str(d) for d in config.distances)
    )
    print(
        "TIE SCENARIO:      "
        + scenario_labels[config.tie_scenario]
    )
    if config.tie_scenario != "none":
        print(
            f"MAX. TIED POSITIONS: {config.max_tie_positions}"
        )
    print(
        f"SKATERS IN 4TH DISTANCE: {config.qualification_limit}"
    )
    print(f"RESERVES:              {config.reserve_count}")
    if config.apply_overall_rank_limit:
        print(
            "CLASSIFICATION LIMIT:     "
            f"top-{config.overall_rank_limit} in classification after three distances only"
        )
        if config.force_outside_top_x_longest_top_y:
            print(
                "TOP-X TRAP:          "
                f"yes: outside top-{config.overall_rank_limit} klassement, "
                f"top-{config.qualification_limit} in longest distance"
            )
        else:
            print("TOP-X TRAP:          no")
    else:
        print(
            "CLASSIFICATION LIMIT:     no additional top-X restriction"
        )
    print(
        "PRACTICE CASE NUMBER:      "
        + (
            str(config.seed)
            if config.seed is not None
            else "random"
        )
    )
    print("=" * 92)


def print_distance_results(
    skaters: list[Skater],
    distances: list[int],
) -> None:
    for distance in distances[:3]:
        ordered = sorted(
            skaters,
            key=lambda skater: (
                status_sort_key(skater.statuses[distance]),
                skater.times[distance]
                if skater.times[distance] is not None
                else float("inf"),
                skater.bib,
            ),
        )

        print(f"\n{distance}m RESULT")
        print("-" * 78)
        print(
            f"{'Pos':<6}"
            f"{'Bib':<6}"
            f"{'Name':<30}"
            f"{'Time/status':<16}"
            f"{'Points':<12}"
        )

        for skater in ordered:
            rank = skater.distance_ranks.get(distance)
            rank_text = str(rank) if rank is not None else "-"
            status = skater.statuses[distance]

            if status == "OK":
                time_or_status = format_time(skater.times[distance])
            elif status == "N/A":
                time_or_status = "-"
            else:
                time_or_status = status

            points_text = (
                f"{skater.points[distance]:.3f}"
                if skater.points[distance] is not None
                else "-"
            )

            print(
                f"{rank_text:<6}"
                f"{skater.bib:<6}"
                f"{skater.name:<30}"
                f"{time_or_status:<16}"
                f"{points_text:<12}"
            )


def print_intermediate_classification(
    skaters: list[Skater],
    distances: list[int],
    number_of_distances: int,
) -> None:
    if number_of_distances not in {2, 3}:
        raise ValueError(
            "Only classifications after two or three distances are supported."
        )

    completed_distances = distances[:number_of_distances]

    title = (
        "CLASSIFICATION AFTER TWO DISTANCES"
        if number_of_distances == 2
        else "CLASSIFICATION AFTER THREE DISTANCES"
    )

    ordered = sorted(
        skaters,
        key=lambda skater: classification_sort_key(
            skater,
            number_of_distances,
        ),
    )

    position_width = 6
    bib_width = 6
    name_width = 28
    time_width = 18
    points_width = 14

    total_width = (
        position_width
        + bib_width
        + name_width
        + time_width * number_of_distances
        + points_width
    )

    print(f"\n{title}")
    print("-" * total_width)

    header = (
        f"{'Pos':<{position_width}}"
        f"{'Bib':<{bib_width}}"
        f"{'Name':<{name_width}}"
    )

    for distance in completed_distances:
        header += f"{str(distance) + ' m':<{time_width}}"

    header += f"{'Total points':<{points_width}}"

    print(header)
    print("-" * total_width)

    for skater in ordered:
        if number_of_distances == 2:
            rank = skater.overall_rank_after_2
            total_points = skater.total_points_after_2
        else:
            rank = skater.overall_rank_after_3
            total_points = skater.total_points_after_3

        rank_text = str(rank) if rank is not None else "-"

        row = (
            f"{rank_text:<{position_width}}"
            f"{skater.bib:<{bib_width}}"
            f"{skater.name:<{name_width}}"
        )

        for distance in completed_distances:
            time_text = format_time_with_rank(skater, distance)
            row += f"{time_text:<{time_width}}"

        points_text = (
            f"{total_points:.3f}"
            if total_points is not None
            else "-"
        )

        row += f"{points_text:<{points_width}}"

        print(row)

    print("-" * total_width)
    print(
        "The rank in each distance is shown in parentheses after the time."
    )


def print_overall_rank_limit_exclusions(
    skaters: list[Skater],
    overall_rank_limit: int | None,
) -> None:
    """
    Laat bij internationale oefeningen zien welke op zichzelf valid
    rijders door de top-X-beperking niet in de selectie mogen worden
    betrokken. Dit helpt bij controle en nabespreking.
    """
    if overall_rank_limit is None:
        return

    excluded = [
        skater
        for skater in eligible_skaters_after_3(skaters)
        if (
            skater.overall_rank_after_3 is not None
            and skater.overall_rank_after_3 > overall_rank_limit
        )
    ]

    if not excluded:
        return

    excluded.sort(
        key=lambda skater: (
            skater.overall_rank_after_3
            if skater.overall_rank_after_3 is not None
            else 999,
            skater.longest_distance_rank
            if skater.longest_distance_rank is not None
            else 999,
        )
    )

    print(
        f"\nNOT ELIGIBLE FOR SELECTION DUE TO TOP-{overall_rank_limit} "
        "LIMIT IN THE CLASSIFICATION AFTER THREE DISTANCES"
    )
    print("-" * 78)
    print(
        f"{'Bib':<6}"
        f"{'Name':<30}"
        f"{'Classification':<16}"
        f"{'Longest distance':<18}"
    )

    for skater in excluded:
        print(
            f"{skater.bib:<6}"
            f"{skater.name:<30}"
            f"{str(skater.overall_rank_after_3):<16}"
            f"{str(skater.longest_distance_rank):<18}"
        )


def print_fourth_distance_selection(
    selected: list[Skater],
    reserves: list[Skater],
) -> None:
    print("\nSELECTION FOR THE FOURTH DISTANCE")
    print("-" * 78)
    print(
        f"{'Nr':<5}"
        f"{'Bib':<6}"
        f"{'Name':<30}"
        f"{'Classification':<14}"
        f"{'Longest distance':<18}"
    )

    for index, skater in enumerate(selected, start=1):
        print(
            f"{index:<5}"
            f"{skater.bib:<6}"
            f"{skater.name:<30}"
            f"{str(skater.overall_rank_after_3):<14}"
            f"{str(skater.longest_distance_rank):<18}"
        )

    if reserves:
        print("\nRESERVES")
        print("-" * 78)

        for index, skater in enumerate(reserves, start=1):
            print(
                f"R{index:<4}"
                f"{skater.bib:<6}"
                f"{skater.name:<30}"
                f"{str(skater.overall_rank_after_3):<14}"
                f"{str(skater.longest_distance_rank):<18}"
            )


def print_script_input(
    skater_data: list[tuple[int, int, str, int]],
) -> None:
    print(
        "\nINPUT VOOR HET BESTAANDE "
        "FOURTH-DISTANCE SCRIPT"
    )
    print("skater_data = [")

    for row in skater_data:
        print(f"    {row},")

    print("]")


# =============================================================================
# EXERCISE GENERATION
# =============================================================================

def generate_exercises(
    config: TournamentConfig,
    incident_messages: list[str],
    tie_messages: list[str],
) -> list[str]:
    longest_completed_distance = max(config.distances[:3])

    exercises = [
        (
            "1. Controleer het tussenklassement na twee afstanden. "
            "Bepaal of de rangschikking en de totaalpunten correct zijn."
        ),
        (
            "2. Based on the classification after two distances, determine "
            "the pairing/order for the third distance."
        ),
        (
            "3. Check the classification after three distances. "
            "Let daarbij op ex aequo's en niet-geklasseerde deelnemers."
        ),
        (
            f"4. Selecteer {config.qualification_limit} deelnemers voor "
            f"de vierde afstand op basis van het tussenklassement en de "
            f"uitslag van de {longest_completed_distance} meter."
        ),
        (
            f"5. Stel een reservelijst met {config.reserve_count} "
            "deelnemers op en motiveer de volgorde."
        ),
        (
            "6. Prepare the start list for the fourth distance and explain "
            "how you determined the pairs and starting order."
        ),
    ]

    if tie_messages:
        exercises.append(
            "7. Leg per ex-aequorank uit welke aanvullende "
            "beslisregel(s) nodig zijn om de situatie correct af te "
            "handelen."
        )

    if incident_messages:
        exercises.append(
            "8. For each incident, assess whether the Skater is still "
            "eligible to remain in the classification and/or for the fourth distance "
            "selection."
        )

    exercises.append(
        "9. Formuleer welke controles je als scheidsrechter uitvoert "
        "voordat je de startlijst ondertekent."
    )

    return exercises


def print_exercises(exercises: list[str]) -> None:
    print("\nPRACTICE QUESTIONS")
    print("=" * 92)

    for exercise in exercises:
        print(exercise)


# =============================================================================
# SAVE OUTPUTS
# =============================================================================

def make_output_basename(config: TournamentConfig) -> str:
    gender_label = "women" if config.gender == "women" else "men"
    distances_label = "-".join(str(d) for d in config.distances)
    seed_label = str(config.seed) if config.seed is not None else "random"

    return (
        f"allround_case_{gender_label}_"
        f"{distances_label}_seed_{seed_label}"
    )


def save_json(
    skaters: list[Skater],
    config: TournamentConfig,
    selected: list[Skater],
    reserves: list[Skater],
    exercises: list[str],
    incident_messages: list[str],
    tie_messages: list[str],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{make_output_basename(config)}.json"

    payload = {
        "config": asdict(config),
        "incidents": incident_messages,
        "tie_scenario_messages": tie_messages,
        "skaters": [asdict(skater) for skater in skaters],
        "selected_bibs": [skater.bib for skater in selected],
        "reserve_bibs": [skater.bib for skater in reserves],
        "exercises": exercises,
        "existing_script_input": make_existing_script_input(skaters),
    }

    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return path


def save_text_report(
    skaters: list[Skater],
    config: TournamentConfig,
    selected: list[Skater],
    reserves: list[Skater],
    exercises: list[str],
    incident_messages: list[str],
    tie_messages: list[str],
    output_dir: Path,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{make_output_basename(config)}.txt"

    lines: list[str] = []
    gender_label = "Women" if config.gender == "women" else "Men"

    lines.append("GEGENEREERDE ALLROUND-OEFENCASUS")
    lines.append("=" * 92)
    lines.append(f"Wedstrijd: {gender_label}")
    lines.append(
        "Distanceen: "
        + " - ".join(str(d) for d in config.distances)
    )
    lines.append(
        f"Deelnemers vierde afstand: {config.qualification_limit}"
    )
    lines.append(f"Reserves: {config.reserve_count}")
    lines.append(f"Seed/oefencasusnummer: {config.seed}")
    lines.append("")

    if incident_messages:
        lines.append("INCIDENTEN")
        lines.append("-" * 92)
        lines.extend(incident_messages)
        lines.append("")

    if tie_messages:
        lines.append("EX-AEQUOSCENARIO")
        lines.append("-" * 92)
        lines.extend(tie_messages)
        lines.append("")

    for number_of_distances in (2, 3):
        completed = config.distances[:number_of_distances]
        lines.append(
            f"TUSSENKLASSEMENT NA {number_of_distances} AFSTANDEN"
        )
        lines.append("-" * 92)

        ordered = sorted(
            skaters,
            key=lambda skater: classification_sort_key(
                skater,
                number_of_distances,
            ),
        )

        for skater in ordered:
            rank = (
                skater.overall_rank_after_2
                if number_of_distances == 2
                else skater.overall_rank_after_3
            )

            total_points = (
                skater.total_points_after_2
                if number_of_distances == 2
                else skater.total_points_after_3
            )

            times = " | ".join(
                f"{distance}m: {format_time_with_rank(skater, distance)}"
                for distance in completed
            )

            lines.append(
                f"{rank or '-':>3} | {skater.bib} | "
                f"{skater.name:<28} | {times} | "
                f"{total_points if total_points is not None else '-'}"
            )

        lines.append("")

    lines.append("SELECTIE VIERDE AFSTAND")
    lines.append("-" * 92)

    for index, skater in enumerate(selected, start=1):
        lines.append(
            f"{index}. {skater.bib} {skater.name} | "
            f"klassement {skater.overall_rank_after_3} | "
            f"langste afstand {skater.longest_distance_rank}"
        )

    if reserves:
        lines.append("")
        lines.append("RESERVES")
        lines.append("-" * 92)

        for index, skater in enumerate(reserves, start=1):
            lines.append(
                f"R{index}. {skater.bib} {skater.name} | "
                f"klassement {skater.overall_rank_after_3} | "
                f"langste afstand {skater.longest_distance_rank}"
            )

    lines.append("")
    lines.append("INPUT BESTAAND FOURTH-DISTANCE SCRIPT")
    lines.append("-" * 92)
    lines.append("skater_data = [")

    for row in make_existing_script_input(skaters):
        lines.append(f"    {row},")

    lines.append("]")

    if exercises:
        lines.append("")
        lines.append("PRACTICE QUESTIONS")
        lines.append("-" * 92)
        lines.extend(exercises)

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    print("=" * 92)
    print("ALLROUND COMBINATION PRACTICE CASE GENERATOR")
    print("=" * 92)

    config = build_config()
    rng = random.Random(config.seed)

    # Bouw de casus volledig op vóórdat we hem accepteren.
    #
    # In v14 werd de internationale top-X-valkuil alleen gecontroleerd
    # tijdens de eerste generatie. Incidenten en geforceerde ex-aequo's
    # konden die situatie daarna weer ongedaan maken. Daarom controleren
    # we vanaf v15 de DEFINITIEVE ranglijsten na incidenten en ex-aequo's.
    #
    # Als de gebruiker de top-X-valkuil expliciet heeft gevraagd, wordt
    # de hele casus opnieuw opgebouwd totdat die valkuil ook echt in de
    # uiteindelijke lijsten aanwezig is.
    max_final_generation_attempts = 150

    skaters: list[Skater] | None = None
    incident_messages: list[str] = []
    pending_fourth_distance_incidents: list[RaceStatus] = []
    tie_messages: list[str] = []

    for _case_attempt in range(max_final_generation_attempts):
        candidate_skaters = create_initial_skaters_with_selection_challenge(
            config,
            rng,
        )

        candidate_incident_messages: list[str] = []
        candidate_pending_fourth: list[RaceStatus] = []

        if config.simulate_incidents:
            (
                candidate_incident_messages,
                candidate_pending_fourth,
            ) = simulate_incidents(
                skaters=candidate_skaters,
                distances=config.distances,
                incident_count=config.incident_count,
                rng=rng,
            )

        recalculate_all(candidate_skaters, config.distances)

        candidate_tie_messages = apply_tie_scenario(
            skaters=candidate_skaters,
            config=config,
            rng=rng,
        )

        recalculate_all(candidate_skaters, config.distances)

        final_selection_challenge_ok = has_meaningful_fourth_distance_selection(
            candidate_skaters,
            config.qualification_limit,
            (
                config.overall_rank_limit
                if config.apply_overall_rank_limit
                else None
            ),
        )

        final_top_x_trap_ok = True
        if (
            config.apply_overall_rank_limit
            and config.force_outside_top_x_longest_top_y
            and config.overall_rank_limit is not None
        ):
            final_top_x_trap_ok = has_outside_top_x_longest_top_y_trap(
                candidate_skaters,
                config.overall_rank_limit,
                config.qualification_limit,
            )

        if final_selection_challenge_ok and final_top_x_trap_ok:
            skaters = candidate_skaters
            incident_messages = candidate_incident_messages
            pending_fourth_distance_incidents = candidate_pending_fourth
            tie_messages = candidate_tie_messages
            break

    if skaters is None:
        raise RuntimeError(
            "Kon na "
            f"{max_final_generation_attempts} pogingen geen casus maken "
            "in which all requested selection challenges remain present after incidents "
            "en ex-aequo's in de definitieve ranglijsten aanwezig zijn. "
            "Try another practice case number or fewer incidents."
        )

    selected, reserves = select_for_fourth_distance(
        skaters=skaters,
        qualification_limit=config.qualification_limit,
        reserve_count=config.reserve_count,
        overall_rank_limit=(
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
    )

    fourth_distance_messages = apply_fourth_distance_incidents(
        selected=selected,
        distances=config.distances,
        pending_statuses=pending_fourth_distance_incidents,
        rng=rng,
    )
    incident_messages.extend(fourth_distance_messages)

    # Herbereken de afstandsuitslagen na eventuele incidenten op afstand 4.
    recalculate_all(skaters, config.distances)

    print_competition_header(config)

    if incident_messages:
        print("\nSIMULATED INCIDENTS")
        print("-" * 92)
        for message in incident_messages:
            print(f"- {message}")

    if tie_messages:
        print("\nFORCED TIE SITUATION")
        print("-" * 92)
        for message in tie_messages:
            print(f"- {message}")

    selection_diagnostics = fourth_distance_selection_diagnostics(
        skaters,
        config.qualification_limit,
        (
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
    )
    if selection_diagnostics:
        print("\nSELECTION PRACTICE CHALLENGE")
        print("-" * 92)
        for message in selection_diagnostics:
            print(f"- {message}")

    international_trap_messages = international_top_x_trap_diagnostics(
        skaters,
        (
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
        config.qualification_limit,
    )
    if international_trap_messages:
        print("\nINTERNATIONAL TOP-X SELECTION TRAP")
        print("-" * 92)
        for message in international_trap_messages:
            print(f"- {message}")
    elif (
        config.apply_overall_rank_limit
        and config.force_outside_top_x_longest_top_y
    ):
        # Dit zou door de definitieve validatie hierboven niet meer
        # mogen voorkomen.
        raise RuntimeError(
            "Interne controlefout: de gevraagde top-X-selectievalkuil "
            "ontbreekt onverwacht in de definitieve ranglijsten."
        )

    print_distance_results(
        skaters=skaters,
        distances=config.distances,
    )

    print_intermediate_classification(
        skaters=skaters,
        distances=config.distances,
        number_of_distances=2,
    )

    print_intermediate_classification(
        skaters=skaters,
        distances=config.distances,
        number_of_distances=3,
    )

    print_overall_rank_limit_exclusions(
        skaters=skaters,
        overall_rank_limit=(
            config.overall_rank_limit
            if config.apply_overall_rank_limit
            else None
        ),
    )

    print_fourth_distance_selection(
        selected=selected,
        reserves=reserves,
    )

    skater_data = make_existing_script_input(skaters)
    print_script_input(skater_data)

    if ask_yes_no(
        "\nDo you want to edit the generated results manually? [y/n]: "
    ):
        manual_edit_menu(
            skaters=skaters,
            config=config,
        )

        # Selectie en reserves opnieuw bepalen na de laatste aanpassing.
        selected, reserves = select_for_fourth_distance(
            skaters=skaters,
            qualification_limit=config.qualification_limit,
            reserve_count=config.reserve_count,
            overall_rank_limit=(
                config.overall_rank_limit
                if config.apply_overall_rank_limit
                else None
            ),
        )

    exercises: list[str] = []

    if config.create_exercises:
        exercises = generate_exercises(
            config=config,
            incident_messages=incident_messages,
            tie_messages=tie_messages,
        )
        print_exercises(exercises)

    if config.save_outputs:
        output_dir = Path("generated_cases")

        text_path = save_text_report(
            skaters=skaters,
            config=config,
            selected=selected,
            reserves=reserves,
            exercises=exercises,
            incident_messages=incident_messages,
            tie_messages=tie_messages,
            output_dir=output_dir,
        )

        json_path = save_json(
            skaters=skaters,
            config=config,
            selected=selected,
            reserves=reserves,
            exercises=exercises,
            incident_messages=incident_messages,
            tie_messages=tie_messages,
            output_dir=output_dir,
        )

        print("\nBESTANDEN OPGESLAGEN")
        print("-" * 92)
        print(f"Tekstrapport: {text_path}")
        print(f"JSON-bestand: {json_path}")

    print("\nKLAAR")
    print("=" * 92)
    print(
        "Controleer oefencasussen altijd aan de hand van de actuele "
        "the applicable ISU Rules and the relevant competition/qualification document."
    )


if __name__ == "__main__":
    main()