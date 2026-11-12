import hashlib
import json
import re
import sqlite3
import uuid

from datetime import datetime, timedelta
from pathlib import Path
from statistics import median


# ============================================================
# VERSION
# ============================================================

SCHEMA_VERSION = 1
DRAFT_SCHEMA_VERSION = 1


# ============================================================
# CHEMINS
# ============================================================

ROOT_DIR = Path(__file__).resolve().parents[1]

MEMORY_DIR = ROOT_DIR / "memory"

DATABASE_FILE = (
    MEMORY_DIR
    / "agent_memory.db"
)

ROUTINES_FILE = (
    ROOT_DIR
    / "config"
    / "routines.json"
)


# ============================================================
# APPRENTISSAGE
# ============================================================

LOOKBACK_DAYS = 21

MULTI_ACTION_MIN_DAYS = 3
SINGLE_ACTION_MIN_DAYS = 5


LEARNABLE_ACTIONS = {
    "open_application",
    "open_website",
}


VALID_SOURCES = {
    "manual",
    "routine",
    "startup",
    "system",
}


# ============================================================
# LABELS
# ============================================================

TARGET_LABELS = {
    "edge": "Edge",
    "vscode": "VS Code",

    "udmci": "UDMCI",
    "teams": "Teams",
    "outlook": "Outlook",
    "outlook-perso": "Outlook personnel",

    "onedrive": "OneDrive",
    "microsoft365": "Microsoft 365",

    "word": "Word",
    "excel": "Excel",
    "powerpoint": "PowerPoint",

    "github": "GitHub",
    "chatgpt": "ChatGPT",

    "gmail": "Gmail",
    "googledrive": "Google Drive",
    "drive": "Google Drive",

    "meet": "Google Meet",
    "calendar": "Google Calendar",

    "youtube": "YouTube",
    "whatsapp": "WhatsApp",
}


DAYPART_LABELS = {
    "morning": "matin",
    "midday": "midi",
    "afternoon": "après-midi",
    "evening": "soir",
    "night": "nuit",
}


# ============================================================
# TEMPS
# ============================================================

def get_local_now():

    return datetime.now().astimezone()


def get_daypart(hour):

    if 5 <= hour < 11:
        return "morning"

    if 11 <= hour < 14:
        return "midday"

    if 14 <= hour < 18:
        return "afternoon"

    if 18 <= hour < 23:
        return "evening"

    return "night"


# ============================================================
# PROFIL ACTIF
# ============================================================

def get_active_profile_name():

    if not ROUTINES_FILE.exists():

        return "unknown"

    try:

        with open(
            ROUTINES_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(
                file
            )

    except (
        OSError,
        json.JSONDecodeError
    ):

        return "unknown"

    profile = data.get(
        "active_profile"
    )

    if not isinstance(
        profile,
        str
    ):

        return "unknown"

    profile = (
        profile
        .lower()
        .strip()
    )

    if not profile:

        return "unknown"

    return profile


# ============================================================
# INITIALISATION SQLITE
# ============================================================

def initialize_database():

    MEMORY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    try:

        connection.execute(
            "PRAGMA journal_mode=WAL;"
        )

        connection.execute(
            "PRAGMA synchronous=NORMAL;"
        )

        connection.execute(
            "PRAGMA foreign_keys=ON;"
        )

        # ====================================================
        # SESSIONS
        # ====================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_sessions (
                id TEXT PRIMARY KEY,

                created_at TEXT NOT NULL,

                local_date TEXT NOT NULL,

                local_time TEXT NOT NULL,

                weekday INTEGER NOT NULL,

                minute_of_day INTEGER NOT NULL,

                daypart TEXT NOT NULL,

                profile TEXT NOT NULL,

                source TEXT NOT NULL,

                signature TEXT NOT NULL,

                actions_json TEXT NOT NULL,

                action_count INTEGER NOT NULL
            );
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_activity_learning
            ON activity_sessions(
                source,
                profile,
                signature,
                daypart,
                created_at
            );
            """
        )

        # ====================================================
        # HABITUDES
        # ====================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                signature TEXT NOT NULL,

                profile TEXT NOT NULL,

                daypart TEXT NOT NULL,

                title TEXT NOT NULL,

                actions_json TEXT NOT NULL,

                occurrences INTEGER NOT NULL,

                distinct_days INTEGER NOT NULL,

                typical_minute INTEGER NOT NULL,

                first_seen TEXT NOT NULL,

                last_seen TEXT NOT NULL,

                status TEXT NOT NULL
                    DEFAULT 'pending',

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                UNIQUE(
                    signature,
                    profile,
                    daypart
                )
            );
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_habit_status
            ON habit_proposals(status);
            """
        )

        # ====================================================
        # BROUILLONS
        # ====================================================

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS habit_drafts (
                proposal_id INTEGER PRIMARY KEY,

                schema_version INTEGER NOT NULL
                    DEFAULT 1,

                name TEXT NOT NULL,

                actions_json TEXT NOT NULL,

                triggers_json TEXT NOT NULL,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                FOREIGN KEY(proposal_id)
                    REFERENCES habit_proposals(id)
                    ON DELETE CASCADE
            );
            """
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# CONNEXION
# ============================================================

def get_connection():

    initialize_database()

    connection = sqlite3.connect(
        DATABASE_FILE
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys=ON;"
    )

    return connection


# ============================================================
# NORMALISATION ACTION
# ============================================================

def normalize_action(
    action_data
):

    if not isinstance(
        action_data,
        dict
    ):

        return None

    if action_data.get(
        "success",
        False
    ) is not True:

        return None

    action = action_data.get(
        "action"
    )

    target = action_data.get(
        "target"
    )

    if not isinstance(
        action,
        str
    ):

        return None

    if not isinstance(
        target,
        str
    ):

        return None

    action = (
        action
        .lower()
        .strip()
    )

    target = (
        target
        .lower()
        .strip()
    )

    if action not in LEARNABLE_ACTIONS:

        return None

    if not target:

        return None

    return {
        "action": action,
        "target": target,
    }


def normalize_actions(
    action_results
):

    actions = []

    seen = set()

    for action_data in action_results:

        normalized = normalize_action(
            action_data
        )

        if normalized is None:
            continue

        key = (
            normalized["action"],
            normalized["target"],
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        actions.append(
            normalized
        )

    return actions


# ============================================================
# SIGNATURE
# ============================================================

def create_signature(
    actions
):

    pairs = []

    for action_data in actions:

        pairs.append(
            (
                action_data["action"],
                action_data["target"],
            )
        )

    pairs.sort()

    payload = json.dumps(
        pairs,
        ensure_ascii=False,
        separators=(",", ":")
    )

    return hashlib.sha256(
        payload.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# TITRES
# ============================================================

def get_target_label(
    target
):

    return TARGET_LABELS.get(
        target,
        target
    )


def build_habit_title(
    actions,
    daypart
):

    labels = [
        get_target_label(
            action_data["target"]
        )
        for action_data in actions
    ]

    period = DAYPART_LABELS.get(
        daypart,
        daypart
    )

    if len(labels) == 1:

        return (
            f"Ouvrir {labels[0]} "
            f"le {period}"
        )

    if len(labels) <= 3:

        return (
            f"Routine {period} : "
            + " + ".join(labels)
        )

    return (
        f"Routine {period} : "
        f"{len(labels)} éléments"
    )


def minute_to_time(
    minute
):

    hour = minute // 60
    minute_value = minute % 60

    return (
        f"{hour:02d}:"
        f"{minute_value:02d}"
    )


# ============================================================
# ENREGISTREMENT SESSION
# ============================================================

def record_session(
    action_results,
    source="manual",
    profile=None
):

    if source not in VALID_SOURCES:

        return (
            False,
            f"Source d'activité invalide : {source}"
        )

    actions = normalize_actions(
        action_results
    )

    if not actions:

        return (
            False,
            (
                "Aucune action apprenable "
                "réussie dans cette session."
            )
        )

    if profile is None:

        profile = get_active_profile_name()

    profile = (
        str(profile)
        .lower()
        .strip()
    )

    if not profile:

        profile = "unknown"

    now = get_local_now()

    minute_of_day = (
        now.hour * 60
        + now.minute
    )

    daypart = get_daypart(
        now.hour
    )

    signature = create_signature(
        actions
    )

    session_id = str(
        uuid.uuid4()
    )

    actions_json = json.dumps(
        actions,
        ensure_ascii=False,
        separators=(",", ":")
    )

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO activity_sessions (
                id,
                created_at,
                local_date,
                local_time,
                weekday,
                minute_of_day,
                daypart,
                profile,
                source,
                signature,
                actions_json,
                action_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                session_id,
                now.isoformat(),
                now.date().isoformat(),
                now.strftime("%H:%M:%S"),
                now.weekday(),
                minute_of_day,
                daypart,
                profile,
                source,
                signature,
                actions_json,
                len(actions),
            )
        )

        connection.commit()

    finally:

        connection.close()

    if source == "manual":

        detect_habits()

    return (
        True,
        session_id
    )


# ============================================================
# DETECTION DES HABITUDES
# ============================================================

def detect_habits():

    now = get_local_now()

    cutoff = (
        now
        - timedelta(
            days=LOOKBACK_DAYS
        )
    )

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM activity_sessions
            WHERE
                source = 'manual'
                AND created_at >= ?
            ORDER BY created_at ASC;
            """,
            (
                cutoff.isoformat(),
            )
        ).fetchall()

        groups = {}

        for row in rows:

            key = (
                row["signature"],
                row["profile"],
                row["daypart"],
            )

            groups.setdefault(
                key,
                []
            )

            groups[key].append(
                row
            )

        new_proposals = []

        for (
            signature,
            profile,
            daypart
        ), group_rows in groups.items():

            if not group_rows:
                continue

            try:

                actions = json.loads(
                    group_rows[-1][
                        "actions_json"
                    ]
                )

            except json.JSONDecodeError:
                continue

            if not isinstance(
                actions,
                list
            ):

                continue

            action_count = len(
                actions
            )

            if action_count == 0:
                continue

            distinct_dates = {
                row["local_date"]
                for row in group_rows
            }

            distinct_days = len(
                distinct_dates
            )

            if action_count == 1:

                required_days = (
                    SINGLE_ACTION_MIN_DAYS
                )

            else:

                required_days = (
                    MULTI_ACTION_MIN_DAYS
                )

            if distinct_days < required_days:
                continue

            minutes = [
                row["minute_of_day"]
                for row in group_rows
            ]

            typical_minute = int(
                median(
                    minutes
                )
            )

            first_seen = (
                group_rows[0][
                    "created_at"
                ]
            )

            last_seen = (
                group_rows[-1][
                    "created_at"
                ]
            )

            title = build_habit_title(
                actions,
                daypart
            )

            actions_json = json.dumps(
                actions,
                ensure_ascii=False,
                separators=(",", ":")
            )

            timestamp = now.isoformat()

            existing = connection.execute(
                """
                SELECT
                    id,
                    status
                FROM habit_proposals
                WHERE
                    signature = ?
                    AND profile = ?
                    AND daypart = ?;
                """,
                (
                    signature,
                    profile,
                    daypart,
                )
            ).fetchone()

            if existing is None:

                cursor = connection.execute(
                    """
                    INSERT INTO habit_proposals (
                        signature,
                        profile,
                        daypart,
                        title,
                        actions_json,
                        occurrences,
                        distinct_days,
                        typical_minute,
                        first_seen,
                        last_seen,
                        status,
                        created_at,
                        updated_at
                    )
                    VALUES (
                        ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, 'pending', ?, ?
                    );
                    """,
                    (
                        signature,
                        profile,
                        daypart,
                        title,
                        actions_json,
                        len(group_rows),
                        distinct_days,
                        typical_minute,
                        first_seen,
                        last_seen,
                        timestamp,
                        timestamp,
                    )
                )

                new_proposals.append(
                    cursor.lastrowid
                )

            else:

                connection.execute(
                    """
                    UPDATE habit_proposals
                    SET
                        title = ?,
                        actions_json = ?,
                        occurrences = ?,
                        distinct_days = ?,
                        typical_minute = ?,
                        first_seen = ?,
                        last_seen = ?,
                        updated_at = ?
                    WHERE id = ?;
                    """,
                    (
                        title,
                        actions_json,
                        len(group_rows),
                        distinct_days,
                        typical_minute,
                        first_seen,
                        last_seen,
                        timestamp,
                        existing["id"],
                    )
                )

        connection.commit()

        return new_proposals

    finally:

        connection.close()


# ============================================================
# HABITUDES
# ============================================================

def get_pending_habits():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM habit_proposals
            WHERE status = 'pending'
            ORDER BY last_seen DESC;
            """
        ).fetchall()

        habits = []

        for row in rows:

            try:

                actions = json.loads(
                    row["actions_json"]
                )

            except json.JSONDecodeError:

                actions = []

            habits.append({
                "id": row["id"],
                "title": row["title"],
                "profile": row["profile"],
                "daypart": row["daypart"],
                "occurrences": row["occurrences"],
                "distinct_days": row["distinct_days"],
                "typical_minute": row["typical_minute"],
                "typical_time": minute_to_time(
                    row["typical_minute"]
                ),
                "first_seen": row["first_seen"],
                "last_seen": row["last_seen"],
                "actions": actions,
                "status": row["status"],
            })

        return habits

    finally:

        connection.close()


def get_pending_habit_by_id(
    proposal_id
):

    try:

        proposal_id = int(
            proposal_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    for habit in get_pending_habits():

        if habit.get(
            "id"
        ) == proposal_id:

            return habit

    return None


# ============================================================
# STATUT
# ============================================================

def set_habit_status(
    proposal_id,
    status
):

    allowed_statuses = {
        "pending",
        "accepted",
        "rejected",
    }

    if status not in allowed_statuses:

        return (
            False,
            f"Statut invalide : {status}"
        )

    try:

        proposal_id = int(
            proposal_id
        )

    except (
        TypeError,
        ValueError
    ):

        return (
            False,
            "Identifiant invalide."
        )

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT id
            FROM habit_proposals
            WHERE id = ?;
            """,
            (
                proposal_id,
            )
        ).fetchone()

        if row is None:

            return (
                False,
                (
                    "Proposition inconnue : "
                    f"{proposal_id}"
                )
            )

        now = get_local_now().isoformat()

        connection.execute(
            """
            UPDATE habit_proposals
            SET
                status = ?,
                updated_at = ?
            WHERE id = ?;
            """,
            (
                status,
                now,
                proposal_id,
            )
        )

        if status in {
            "accepted",
            "rejected",
        }:

            connection.execute(
                """
                DELETE FROM habit_drafts
                WHERE proposal_id = ?;
                """,
                (
                    proposal_id,
                )
            )

        connection.commit()

        return (
            True,
            f"Statut mis à jour : {status}"
        )

    finally:

        connection.close()


# ============================================================
# BROUILLON : CREATION
# ============================================================

def create_habit_draft(
    proposal_id
):

    habit = get_pending_habit_by_id(
        proposal_id
    )

    if habit is None:

        return (
            False,
            None,
            (
                "Habitude inexistante "
                "ou déjà traitée."
            )
        )

    existing = get_habit_draft(
        proposal_id
    )

    if existing is not None:

        return (
            True,
            existing,
            (
                "Un brouillon existe déjà "
                "pour cette habitude."
            )
        )

    actions = habit.get(
        "actions",
        []
    )

    if not actions:

        return (
            False,
            None,
            (
                "Cette habitude ne contient "
                "aucune action."
            )
        )

    name = habit.get(
        "title"
    )

    if not isinstance(
        name,
        str
    ) or not name.strip():

        name = (
            f"Habitude {proposal_id}"
        )

    triggers = [
        f"lance habitude {proposal_id}",
        f"routine habitude {proposal_id}",
    ]

    now = get_local_now().isoformat()

    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO habit_drafts (
                proposal_id,
                schema_version,
                name,
                actions_json,
                triggers_json,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                int(proposal_id),

                DRAFT_SCHEMA_VERSION,

                name.strip(),

                json.dumps(
                    actions,
                    ensure_ascii=False,
                    separators=(",", ":")
                ),

                json.dumps(
                    triggers,
                    ensure_ascii=False,
                    separators=(",", ":")
                ),

                now,
                now,
            )
        )

        connection.commit()

    finally:

        connection.close()

    return (
        True,
        get_habit_draft(
            proposal_id
        ),
        "Brouillon créé."
    )


# ============================================================
# BROUILLON : LECTURE
# ============================================================

def get_habit_draft(
    proposal_id
):

    try:

        proposal_id = int(
            proposal_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM habit_drafts
            WHERE proposal_id = ?;
            """,
            (
                proposal_id,
            )
        ).fetchone()

        if row is None:
            return None

        try:

            actions = json.loads(
                row["actions_json"]
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):

            actions = []

        try:

            triggers = json.loads(
                row["triggers_json"]
            )

        except (
            json.JSONDecodeError,
            TypeError
        ):

            triggers = []

        return {
            "proposal_id": row["proposal_id"],
            "schema_version": row["schema_version"],
            "name": row["name"],
            "actions": actions,
            "triggers": triggers,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    finally:

        connection.close()


# ============================================================
# BROUILLON : LISTE
# ============================================================

def get_habit_drafts():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT proposal_id
            FROM habit_drafts
            ORDER BY updated_at DESC;
            """
        ).fetchall()

        ids = [
            row["proposal_id"]
            for row in rows
        ]

    finally:

        connection.close()

    drafts = []

    for proposal_id in ids:

        draft = get_habit_draft(
            proposal_id
        )

        if draft is not None:

            drafts.append(
                draft
            )

    return drafts


# ============================================================
# VALIDATION CIBLE
# ============================================================

def is_valid_draft_target(
    target
):

    if not isinstance(
        target,
        str
    ):

        return False

    target = (
        target
        .lower()
        .strip()
    )

    if not target:

        return False

    return bool(
        re.fullmatch(
            r"[a-z0-9_.-]+",
            target
        )
    )


# ============================================================
# BROUILLON : NOM
# ============================================================

def update_habit_draft_name(
    proposal_id,
    new_name
):

    if not isinstance(
        new_name,
        str
    ):

        return (
            False,
            "Nom invalide."
        )

    new_name = new_name.strip()

    if not new_name:

        return (
            False,
            "Le nom ne peut pas être vide."
        )

    if len(new_name) > 120:

        return (
            False,
            "Le nom est trop long."
        )

    if get_habit_draft(
        proposal_id
    ) is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE habit_drafts
            SET
                name = ?,
                updated_at = ?
            WHERE proposal_id = ?;
            """,
            (
                new_name,
                get_local_now().isoformat(),
                int(proposal_id),
            )
        )

        connection.commit()

    finally:

        connection.close()

    return (
        True,
        "Nom du brouillon modifié."
    )


# ============================================================
# BROUILLON : DECLENCHEURS
# ============================================================

def update_habit_draft_triggers(
    proposal_id,
    triggers
):

    if not isinstance(
        triggers,
        list
    ):

        return (
            False,
            (
                "Liste de déclencheurs "
                "invalide."
            )
        )

    clean_triggers = []

    seen = set()

    for trigger in triggers:

        if not isinstance(
            trigger,
            str
        ):

            continue

        trigger = trigger.strip()

        if not trigger:
            continue

        if len(trigger) > 120:
            continue

        key = trigger.lower()

        if key in seen:
            continue

        seen.add(
            key
        )

        clean_triggers.append(
            trigger
        )

    if not clean_triggers:

        return (
            False,
            (
                "Au moins un déclencheur "
                "est nécessaire."
            )
        )

    if get_habit_draft(
        proposal_id
    ) is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE habit_drafts
            SET
                triggers_json = ?,
                updated_at = ?
            WHERE proposal_id = ?;
            """,
            (
                json.dumps(
                    clean_triggers,
                    ensure_ascii=False,
                    separators=(",", ":")
                ),

                get_local_now().isoformat(),

                int(proposal_id),
            )
        )

        connection.commit()

    finally:

        connection.close()

    return (
        True,
        "Déclencheur du brouillon modifié."
    )


def set_habit_draft_trigger(
    proposal_id,
    trigger
):

    return update_habit_draft_triggers(
        proposal_id,
        [
            trigger
        ]
    )


# ============================================================
# BROUILLON : ACTIONS
# ============================================================

def update_habit_draft_actions(
    proposal_id,
    actions
):

    if not isinstance(
        actions,
        list
    ):

        return (
            False,
            "Liste d'actions invalide."
        )

    clean_actions = []

    seen = set()

    for action_data in actions:

        if not isinstance(
            action_data,
            dict
        ):

            return (
                False,
                "Action invalide."
            )

        action = action_data.get(
            "action"
        )

        target = action_data.get(
            "target"
        )

        if not isinstance(
            action,
            str
        ):

            return (
                False,
                "Action manquante."
            )

        if not isinstance(
            target,
            str
        ):

            return (
                False,
                "Cible manquante."
            )

        action = (
            action
            .lower()
            .strip()
        )

        target = (
            target
            .lower()
            .strip()
        )

        if action not in LEARNABLE_ACTIONS:

            return (
                False,
                (
                    "Action interdite : "
                    f"{action}"
                )
            )

        if not is_valid_draft_target(
            target
        ):

            return (
                False,
                (
                    "Cible invalide : "
                    f"{target}"
                )
            )

        key = (
            action,
            target
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        clean_actions.append({
            "action": action,
            "target": target,
        })

    if not clean_actions:

        return (
            False,
            (
                "Le brouillon doit conserver "
                "au moins une action."
            )
        )

    if get_habit_draft(
        proposal_id
    ) is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE habit_drafts
            SET
                actions_json = ?,
                updated_at = ?
            WHERE proposal_id = ?;
            """,
            (
                json.dumps(
                    clean_actions,
                    ensure_ascii=False,
                    separators=(",", ":")
                ),

                get_local_now().isoformat(),

                int(proposal_id),
            )
        )

        connection.commit()

    finally:

        connection.close()

    return (
        True,
        "Actions du brouillon modifiées."
    )


# ============================================================
# AJOUT D'UNE ACTION
# ============================================================

def add_habit_draft_action(
    proposal_id,
    action,
    target
):

    draft = get_habit_draft(
        proposal_id
    )

    if draft is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    if action not in LEARNABLE_ACTIONS:

        return (
            False,
            (
                "Action interdite dans "
                "une habitude."
            )
        )

    if not is_valid_draft_target(
        target
    ):

        return (
            False,
            "Cible invalide."
        )

    actions = list(
        draft.get(
            "actions",
            []
        )
    )

    new_action = {
        "action": action,
        "target": target,
    }

    if new_action in actions:

        return (
            False,
            (
                "Cette action existe déjà "
                "dans le brouillon."
            )
        )

    actions.append(
        new_action
    )

    return update_habit_draft_actions(
        proposal_id,
        actions
    )


# ============================================================
# RETRAIT D'UNE ACTION
# ============================================================

def remove_habit_draft_action(
    proposal_id,
    action,
    target
):

    draft = get_habit_draft(
        proposal_id
    )

    if draft is None:

        return (
            False,
            (
                "Aucun brouillon pour "
                "cette habitude."
            )
        )

    actions = draft.get(
        "actions",
        []
    )

    remaining = []

    removed = False

    for action_data in actions:

        if (
            action_data.get("action") == action
            and
            action_data.get("target") == target
        ):

            removed = True
            continue

        remaining.append(
            action_data
        )

    if not removed:

        return (
            False,
            (
                "Cette action n'existe pas "
                "dans le brouillon."
            )
        )

    if not remaining:

        return (
            False,
            (
                "Impossible de retirer "
                "la dernière action du brouillon."
            )
        )

    return update_habit_draft_actions(
        proposal_id,
        remaining
    )


# ============================================================
# SUPPRESSION BROUILLON
# ============================================================

def delete_habit_draft(
    proposal_id
):

    try:

        proposal_id = int(
            proposal_id
        )

    except (
        TypeError,
        ValueError
    ):

        return (
            False,
            "Identifiant invalide."
        )

    connection = get_connection()

    try:

        cursor = connection.execute(
            """
            DELETE FROM habit_drafts
            WHERE proposal_id = ?;
            """,
            (
                proposal_id,
            )
        )

        connection.commit()

        if cursor.rowcount == 0:

            return (
                False,
                "Aucun brouillon à supprimer."
            )

    finally:

        connection.close()

    return (
        True,
        (
            "Modification annulée. "
            "Le brouillon a été supprimé."
        )
    )


# ============================================================
# FORMAT BROUILLON
# ============================================================

def format_habit_draft(
    draft
):

    if not isinstance(
        draft,
        dict
    ):

        return "Brouillon invalide."

    lines = [
        "=" * 60,
        "BROUILLON D'HABITUDE",
        "=" * 60,
        "",
        (
            "Habitude : "
            f"{draft.get('proposal_id')}"
        ),
        (
            "Nom : "
            f"{draft.get('name')}"
        ),
        "",
        "Actions :",
    ]

    actions = draft.get(
        "actions",
        []
    )

    if not actions:

        lines.append(
            "  Aucune action"
        )

    else:

        for index, action_data in enumerate(
            actions,
            start=1
        ):

            lines.append(
                (
                    f"  {index}. "
                    f"{action_data.get('action')} "
                    f"-> "
                    f"{action_data.get('target')}"
                )
            )

    lines.append("")
    lines.append("Déclencheurs :")

    triggers = draft.get(
        "triggers",
        []
    )

    if not triggers:

        lines.append(
            "  Aucun déclencheur"
        )

    else:

        for index, trigger in enumerate(
            triggers,
            start=1
        ):

            lines.append(
                (
                    f"  {index}. "
                    f"{trigger}"
                )
            )

    return "\n".join(
        lines
    )


# ============================================================
# RESUME
# ============================================================

def get_learning_summary():

    connection = get_connection()

    try:

        manual_sessions = connection.execute(
            """
            SELECT COUNT(*)
            FROM activity_sessions
            WHERE source = 'manual';
            """
        ).fetchone()[0]

        pending = connection.execute(
            """
            SELECT COUNT(*)
            FROM habit_proposals
            WHERE status = 'pending';
            """
        ).fetchone()[0]

        accepted = connection.execute(
            """
            SELECT COUNT(*)
            FROM habit_proposals
            WHERE status = 'accepted';
            """
        ).fetchone()[0]

        rejected = connection.execute(
            """
            SELECT COUNT(*)
            FROM habit_proposals
            WHERE status = 'rejected';
            """
        ).fetchone()[0]

        drafts = connection.execute(
            """
            SELECT COUNT(*)
            FROM habit_drafts;
            """
        ).fetchone()[0]

        return {
            "manual_sessions": manual_sessions,
            "pending": pending,
            "accepted": accepted,
            "rejected": rejected,
            "drafts": drafts,
        }

    finally:

        connection.close()


# ============================================================
# AFFICHAGE
# ============================================================

def print_pending_habits():

    habits = get_pending_habits()

    if not habits:

        print(
            "Aucune habitude proposée."
        )

        return

    for habit in habits:

        print()
        print(
            f"Proposition #{habit['id']}"
        )

        print(
            "Nom :",
            habit["title"]
        )

        print(
            "Profil :",
            habit["profile"]
        )

        print(
            "Jours observés :",
            habit["distinct_days"]
        )

        print(
            "Occurrences :",
            habit["occurrences"]
        )

        print(
            "Heure typique :",
            habit["typical_time"]
        )

        print(
            "Actions :"
        )

        for action_data in habit["actions"]:

            print(
                (
                    "  - "
                    f"{action_data['action']} "
                    f"-> {action_data['target']}"
                )
            )


# ============================================================
# TEST
# ============================================================

def main():

    initialize_database()

    print()

    print(
        "=" * 60
    )

    print(
        "APPRENTISSAGE LOCAL - AgentLocal"
    )

    print(
        "=" * 60
    )

    print()

    print(
        "Base :"
    )

    print(
        DATABASE_FILE
    )

    print()

    summary = get_learning_summary()

    print(
        "Sessions manuelles :",
        summary["manual_sessions"]
    )

    print(
        "Habitudes en attente :",
        summary["pending"]
    )

    print(
        "Habitudes acceptées :",
        summary["accepted"]
    )

    print(
        "Habitudes refusées :",
        summary["rejected"]
    )

    print(
        "Brouillons :",
        summary["drafts"]
    )

    print()

    print(
        "-" * 60
    )

    print_pending_habits()

    drafts = get_habit_drafts()

    if drafts:

        print()

        print(
            "-" * 60
        )

        print(
            "BROUILLONS"
        )

        for draft in drafts:

            print()

            print(
                format_habit_draft(
                    draft
                )
            )


if __name__ == "__main__":

    main()