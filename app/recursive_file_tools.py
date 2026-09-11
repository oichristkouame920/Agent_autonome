import os
import re
import shutil
import unicodedata
from pathlib import Path

import file_tools as base


# ============================================================
# ACCES RECURSIF CONTROLE AUX RACINES UTILISATEUR
# ============================================================

DEFAULT_SEARCH_ROOTS = (
    "desktop",
    "documents",
    "downloads",
    "pictures",
    "videos",
    "music",
)

HARD_MAX_RECURSIVE_DEPTH = 16
HARD_MAX_SEARCH_ENTRIES = 20000
HARD_MAX_SEARCH_RESULTS = 50
HARD_MAX_RELATIVE_PATH_LENGTH = 1024


def get_recursive_access_policy():
    policy = (
        base.get_filesystem_config()
        .get("recursive_access_policy", {})
    )
    return policy if isinstance(policy, dict) else {}


def _positive_bounded_int(value, default, hard_max):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value <= 0:
        return default
    return min(value, hard_max)


def _recursive_limits():
    policy = get_recursive_access_policy()
    max_depth = _positive_bounded_int(
        policy.get("maximum_depth", 10),
        10,
        HARD_MAX_RECURSIVE_DEPTH,
    )
    max_entries = _positive_bounded_int(
        policy.get("maximum_search_entries", 6000),
        6000,
        HARD_MAX_SEARCH_ENTRIES,
    )
    max_results = _positive_bounded_int(
        policy.get("maximum_search_results", 20),
        20,
        HARD_MAX_SEARCH_RESULTS,
    )
    return max_depth, max_entries, max_results


def _policy_allows_recursive_access():
    policy = get_recursive_access_policy()
    if not base.is_filesystem_enabled():
        return False
    if not policy.get("enabled", False):
        return False
    if not policy.get("allow_nested_paths", False):
        return False
    if policy.get("allow_absolute_paths", False):
        return False
    if policy.get("follow_symbolic_links", False):
        return False
    if policy.get("follow_junctions", False):
        return False
    if policy.get("follow_reparse_points", False):
        return False
    return True


def normalize_relative_path(value, allow_empty=False):
    """
    Valide un chemin RELATIF à une des six racines autorisées.

    Exemples acceptés :
        Cours\\Master1\\rapport.docx
        Cours/Module1/notes.txt

    Exemples refusés :
        C:\\Windows\\...
        \\serveur\\partage
        ..\\Windows
        Cours\\*\\rapport.pdf
    """
    if value is None:
        value = ""

    if not isinstance(value, str):
        return False, "Le chemin relatif est invalide."

    value = value.strip()

    if not value:
        if allow_empty:
            return True, ""
        return False, "Le chemin relatif est vide."

    if len(value) > HARD_MAX_RELATIVE_PATH_LENGTH:
        return False, "Le chemin relatif est trop long."

    if value.startswith(("\\\\", "//", "\\", "/")):
        return False, "Les chemins absolus ou réseau sont interdits."

    # Lettre de lecteur ou Alternate Data Stream.
    if ":" in value:
        return False, "Les lettres de lecteur et Alternate Data Streams sont interdits."

    if "*" in value or "?" in value:
        return False, "Les jokers sont interdits."

    raw_parts = value.replace("/", "\\").split("\\")

    if any(part == "" for part in raw_parts):
        return False, "Le chemin contient un composant vide."

    max_depth, _, _ = _recursive_limits()
    if len(raw_parts) > max_depth:
        return False, f"Le chemin dépasse la profondeur maximale autorisée ({max_depth})."

    clean_parts = []

    for part in raw_parts:
        if part in {".", ".."}:
            return False, "Les composants '.' et '..' sont interdits."

        valid, cleaned = base.validate_simple_name(part)
        if not valid:
            return False, cleaned

        clean_parts.append(cleaned)

    return True, "\\".join(clean_parts)


def _parts(relative_path):
    if not relative_path:
        return []
    return relative_path.replace("/", "\\").split("\\")


def _root_path(root_name):
    root_name = str(root_name).strip().lower()
    root = base.resolve_allowed_root(root_name)
    if root is None:
        return None, "Dossier racine protégé, inconnu ou introuvable."
    try:
        root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return None, "Impossible de vérifier la racine autorisée."
    if not root.is_dir():
        return None, "La racine autorisée n'est pas un dossier."
    if base.is_hard_protected_path(root):
        return None, "La racine appartient à une zone protégée."
    return root, None


def _check_existing_component(path, allow_file=False):
    if base.is_hard_protected_path(path):
        return False, "Une zone système ou protégée a été détectée."
    if base.is_reparse_point(path):
        return False, "Les liens, junctions et reparse points sont interdits."
    if base.is_hidden_or_system(path):
        return False, "Les éléments cachés ou système sont protégés."
    if not allow_file and not path.is_dir():
        return False, "Un composant du chemin n'est pas un dossier."
    return True, None


def resolve_existing_inside_root(root_name, relative_path, expected="any", allow_root=False):
    """Résout un élément existant sans jamais sortir de la racine autorisée."""
    if not _policy_allows_recursive_access():
        return False, "L'accès récursif contrôlé est désactivé."

    root, error = _root_path(root_name)
    if root is None:
        return False, error

    valid, rel = normalize_relative_path(relative_path, allow_empty=allow_root)
    if not valid:
        return False, rel

    if not rel:
        if not allow_root:
            return False, "La racine elle-même n'est pas une cible autorisée pour cette action."
        return True, root

    current = root
    path_parts = _parts(rel)

    for index, component in enumerate(path_parts):
        current = current / component

        if not os.path.lexists(str(current)):
            return False, f"L'élément '{rel}' n'existe pas."

        is_last = index == len(path_parts) - 1
        ok, component_error = _check_existing_component(
            current,
            allow_file=(is_last and expected in {"any", "file"}),
        )
        if not ok:
            return False, component_error

    try:
        resolved = current.resolve(strict=True)
    except (OSError, RuntimeError):
        return False, "Impossible de résoudre le chemin demandé."

    if not base.is_same_or_descendant(resolved, root) or base.is_same_path(resolved, root):
        return False, "Le chemin sort de la racine autorisée."

    if expected == "file" and not resolved.is_file():
        return False, "La cible n'est pas un fichier normal autorisé."

    if expected == "dir" and not resolved.is_dir():
        return False, "La cible n'est pas un dossier autorisé."

    return True, resolved


def resolve_existing_directory(root_name, relative_path=""):
    return resolve_existing_inside_root(
        root_name,
        relative_path,
        expected="dir",
        allow_root=True,
    )


def resolve_new_leaf_inside_root(root_name, relative_path, leaf_kind="file"):
    """Résout une destination inexistante dont le parent doit déjà exister."""
    if not _policy_allows_recursive_access():
        return False, "L'accès récursif contrôlé est désactivé."

    valid, rel = normalize_relative_path(relative_path, allow_empty=False)
    if not valid:
        return False, rel

    path_parts = _parts(rel)
    leaf = path_parts[-1]
    parent_rel = "\\".join(path_parts[:-1])

    ok, parent = resolve_existing_directory(root_name, parent_rel)
    if not ok:
        return False, parent

    target = parent / leaf

    if base.is_hard_protected_path(target):
        return False, "La destination appartient à une zone protégée."

    if os.path.lexists(str(target)):
        return False, f"'{rel}' existe déjà. Aucun écrasement n'est autorisé."

    root, error = _root_path(root_name)
    if root is None:
        return False, error

    try:
        resolved_parent = parent.resolve(strict=True)
        candidate = (resolved_parent / leaf).resolve(strict=False)
    except (OSError, RuntimeError):
        return False, "Impossible de vérifier la destination."

    if not base.is_same_or_descendant(candidate, root) or base.is_same_path(candidate, root):
        return False, "La destination sort de la racine autorisée."

    if leaf_kind == "file":
        valid_leaf, result = base.validate_file_name(leaf)
    else:
        valid_leaf, result = base.validate_folder_name(leaf)

    if not valid_leaf:
        return False, result

    return True, target


def relative_display(root_name, path):
    root, _ = _root_path(root_name)
    try:
        rel = path.resolve(strict=False).relative_to(root)
        rel_text = str(rel)
    except Exception:
        rel_text = path.name
    return f"{base.DISPLAY_NAMES.get(root_name, root_name)}\\{rel_text}"


def _manual_policy_check(policy, explicit_user_command, source="manual", action_label="L'action"):
    source = str(source).strip().lower()
    if source != "manual":
        return False, f"{action_label} est réservée aux commandes manuelles explicites."
    if policy.get("require_explicit_user_command", True) and not explicit_user_command:
        return False, f"{action_label} nécessite une commande explicite de l'utilisateur."
    if policy.get("allow_from_routine", False):
        return False, "Configuration dangereuse détectée : les routines doivent rester désactivées."
    if policy.get("allow_from_habit", False):
        return False, "Configuration dangereuse détectée : les habitudes doivent rester désactivées."
    if policy.get("maximum_items_per_command", 1) != 1:
        return False, "Un seul élément doit être autorisé par commande."
    return True, None



# ============================================================
# REFERENCES DE FICHIERS EN LANGAGE NATUREL
# ============================================================

HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS = 3


def get_file_reference_policy():
    policy = (
        base.get_filesystem_config()
        .get("file_reference_policy", {})
    )
    return policy if isinstance(policy, dict) else {}


def _file_reference_policy_enabled():
    policy = get_file_reference_policy()
    return bool(
        policy.get("enabled", False)
        and policy.get("allow_missing_extension", False)
        and policy.get("require_unique_match", True)
        and not policy.get("allow_fuzzy_typo_matching", False)
    )


def _normalize_reference_text(value):
    """Normalisation de recherche uniquement, jamais utilisee comme chemin reel."""
    if not isinstance(value, str):
        return ""

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.casefold()

    # Les separateurs courants dans les noms de fichiers deviennent des espaces.
    value = re.sub(r"[._\-()\[\]{}]+", " ", value)
    value = "".join(
        character if character.isalnum() else " "
        for character in value
    )
    return " ".join(value.split())


def _reference_compact_length(value):
    return len(
        "".join(
            character
            for character in _normalize_reference_text(value)
            if character.isalnum()
        )
    )


def _validate_file_reference(reference):
    valid, cleaned = base.validate_simple_name(reference)
    if not valid:
        return False, cleaned

    policy = get_file_reference_policy()
    try:
        minimum = int(
            policy.get(
                "minimum_partial_characters",
                HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS,
            )
        )
    except (TypeError, ValueError):
        minimum = HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS

    minimum = max(
        HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS,
        min(minimum, 32),
    )

    # Un nom exact tres court reste utilisable. La limite minimale ne sera
    # appliquee que si la resolution doit passer par une correspondance partielle.
    return True, cleaned


def _file_reference_match_tier(reference, candidate_name):
    """
    Renvoie un niveau de correspondance, le plus petit etant le meilleur.

    0 : nom complet exact, extension comprise
    1 : nom sans extension exact
    2 : debut du nom sans extension
    3 : tous les mots demandes correspondent au debut de mots du nom
    4 : sous-chaine normalisee dans le nom sans extension

    Aucune distance de Levenshtein ni correction automatique de faute n'est
    utilisee afin de ne jamais choisir un fichier sur une ressemblance vague.
    """
    if not isinstance(reference, str) or not isinstance(candidate_name, str):
        return None

    reference = reference.strip()
    candidate_name = candidate_name.strip()

    if not reference or not candidate_name:
        return None

    if unicodedata.normalize("NFC", reference).casefold() == unicodedata.normalize(
        "NFC", candidate_name
    ).casefold():
        return 0

    reference_normalized = _normalize_reference_text(reference)
    stem_normalized = _normalize_reference_text(Path(candidate_name).stem)

    if not reference_normalized or not stem_normalized:
        return None

    if reference_normalized == stem_normalized:
        return 1

    policy = get_file_reference_policy()
    if not policy.get("allow_partial_name", False):
        return None

    try:
        minimum = int(
            policy.get(
                "minimum_partial_characters",
                HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS,
            )
        )
    except (TypeError, ValueError):
        minimum = HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS

    minimum = max(
        HARD_MIN_PARTIAL_FILE_REFERENCE_CHARS,
        min(minimum, 32),
    )

    if _reference_compact_length(reference) < minimum:
        return None

    if stem_normalized.startswith(reference_normalized):
        return 2

    requested_tokens = reference_normalized.split()
    candidate_tokens = stem_normalized.split()

    if requested_tokens and candidate_tokens:
        token_match = all(
            any(candidate_token.startswith(requested_token) for candidate_token in candidate_tokens)
            for requested_token in requested_tokens
        )
        if token_match:
            return 3

    if reference_normalized in stem_normalized:
        return 4

    return None


def _search_file_reference(
    reference,
    root_name=None,
    start_relative=None,
    recursive=True,
):
    """
    Recherche une reference de fichier dans les racines autorisees.

    La recherche peut utiliser un nom exact, un nom sans extension ou un
    fragment de nom. Seul le meilleur niveau de correspondance est renvoye.
    """
    if not _file_reference_policy_enabled():
        return False, "La resolution naturelle des noms de fichiers est desactivee.", [], False, None

    valid, cleaned_reference = _validate_file_reference(reference)
    if not valid:
        return False, cleaned_reference, [], False, None

    policy = get_recursive_access_policy()
    if not _policy_allows_recursive_access() or not policy.get("allow_recursive_search", False):
        return False, "La recherche recursive est desactivee.", [], False, None

    configured_roots = policy.get("auto_discovery_roots", list(DEFAULT_SEARCH_ROOTS))
    if not isinstance(configured_roots, list):
        configured_roots = list(DEFAULT_SEARCH_ROOTS)

    hard_roots = [root for root in DEFAULT_SEARCH_ROOTS if root in configured_roots]
    roots = [str(root_name).strip().lower()] if root_name else hard_roots

    max_depth, max_entries, max_results = _recursive_limits()
    matches_by_tier = {0: [], 1: [], 2: [], 3: [], 4: []}
    scanned = 0
    limit_reached = False

    for root in roots:
        if root not in DEFAULT_SEARCH_ROOTS:
            return False, "Racine de recherche inconnue.", [], False, None
        if not base.get_root_permissions(root).get("enabled", False):
            continue

        root_path, error = _root_path(root)
        if root_path is None:
            continue

        if start_relative is not None:
            ok, start_path = resolve_existing_directory(root, start_relative)
            if not ok:
                return False, start_path, [], False, None
        else:
            start_path = root_path

        stack = [(start_path, 0)]

        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue

            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        scanned += 1
                        if scanned > max_entries:
                            limit_reached = True
                            stack.clear()
                            break

                        path = Path(entry.path)

                        try:
                            if base.is_hard_protected_path(path):
                                continue
                            if base.is_reparse_point(path):
                                continue
                            if base.is_hidden_or_system(path):
                                continue

                            is_dir = entry.is_dir(follow_symlinks=False)
                            is_file = entry.is_file(follow_symlinks=False)
                        except OSError:
                            continue

                        if is_file:
                            tier = _file_reference_match_tier(
                                cleaned_reference,
                                entry.name,
                            )
                            if tier is not None:
                                matches_by_tier[tier].append((root, path))
                                total_matches = sum(len(items) for items in matches_by_tier.values())
                                if total_matches >= max_results:
                                    limit_reached = True
                                    stack.clear()
                                    break

                        if recursive and is_dir and depth < max_depth:
                            stack.append((path, depth + 1))

            except (OSError, PermissionError):
                continue

            if limit_reached:
                break

        if limit_reached:
            break

    best_tier = None
    best_matches = []
    for tier in (0, 1, 2, 3, 4):
        if matches_by_tier[tier]:
            best_tier = tier
            best_matches = matches_by_tier[tier]
            break

    return True, None, best_matches, limit_reached, best_tier


def _unique_file_candidate(
    file_name,
    root_name=None,
    start_relative=None,
    recursive=True,
):
    success, error, matches, limited, tier = _search_file_reference(
        file_name,
        root_name=root_name,
        start_relative=start_relative,
        recursive=recursive,
    )
    if not success:
        return False, error

    if not matches:
        suffix = " La limite de recherche a ete atteinte." if limited else ""
        where = f" dans {base.DISPLAY_NAMES.get(root_name, root_name)}" if root_name else ""
        return False, f"Aucun fichier correspondant a '{file_name}' n'a ete trouve{where}.{suffix}"

    if len(matches) != 1:
        locations = ", ".join(
            relative_display(root, path)
            for root, path in matches[:10]
        )
        return False, (
            f"Plusieurs fichiers correspondent a '{file_name}' : {locations}. "
            "Precise davantage le nom ou le dossier pour eviter d'agir sur le mauvais fichier."
        )

    # Si le parcours n'a pas pu etre termine, on ne conclut pas a l'unicite.
    if limited:
        return False, (
            f"Un fichier correspondant a '{file_name}' a ete trouve, mais la recherche "
            "a atteint sa limite de securite. Precise davantage le nom ou le dossier."
        )

    return True, matches[0]


def resolve_file_reference_inside_root(root_name, file_reference):
    """
    Resout un fichier existant dans une racine autorisee.

    - chemin exact : prioritaire ;
    - nom simple : recherche recursive dans la racine ;
    - chemin avec parent explicite : recherche uniquement dans ce parent,
      sans descendre plus bas, si le dernier composant est incomplet.
    """
    valid, relative = normalize_relative_path(file_reference, allow_empty=False)
    if not valid:
        return False, relative

    exact_ok, exact_path = resolve_existing_inside_root(
        root_name,
        relative,
        expected="file",
        allow_root=False,
    )
    if exact_ok:
        return True, exact_path

    path_parts = _parts(relative)
    leaf_reference = path_parts[-1]
    parent_relative = "\\".join(path_parts[:-1])

    if parent_relative:
        ok, candidate = _unique_file_candidate(
            leaf_reference,
            root_name=root_name,
            start_relative=parent_relative,
            recursive=False,
        )
    else:
        ok, candidate = _unique_file_candidate(
            leaf_reference,
            root_name=root_name,
            start_relative=None,
            recursive=True,
        )

    if not ok:
        return False, candidate

    _, path = candidate
    return True, path


def _resolved_rename_destination_name(source_path, requested_new_name):
    """Preserve l'extension existante si l'utilisateur ne la retape pas."""
    valid, cleaned_new_name = base.validate_file_name(requested_new_name)
    if not valid:
        return False, cleaned_new_name

    policy = get_file_reference_policy()
    preserve_extension = policy.get(
        "preserve_extension_on_rename_when_omitted",
        True,
    )

    requested_extension_chain = base.get_extension_chain(cleaned_new_name)
    source_extension_chain = base.get_extension_chain(source_path.name)

    if preserve_extension and not requested_extension_chain and source_extension_chain:
        original_suffix = "".join(source_path.suffixes)
        cleaned_new_name = cleaned_new_name + original_suffix
        valid, cleaned_new_name = base.validate_file_name(cleaned_new_name)
        if not valid:
            return False, cleaned_new_name

    return True, cleaned_new_name


# ============================================================
# RECHERCHE RECURSIVE CONTROLEE
# ============================================================

def _search_exact(name, root_name=None, item_type="any"):
    valid_name, cleaned_name = base.validate_simple_name(name)
    if not valid_name:
        return False, cleaned_name, [], False

    item_type = str(item_type).strip().lower()
    if item_type not in {"any", "file", "dir"}:
        return False, "Type de recherche invalide.", [], False

    policy = get_recursive_access_policy()
    if not _policy_allows_recursive_access() or not policy.get("allow_recursive_search", False):
        return False, "La recherche récursive est désactivée.", [], False

    roots = [str(root_name).strip().lower()] if root_name else list(DEFAULT_SEARCH_ROOTS)
    max_depth, max_entries, max_results = _recursive_limits()
    matches = []
    scanned = 0
    limit_reached = False
    wanted = cleaned_name.casefold()

    for root in roots:
        if root not in base.KNOWN_FOLDER_GUIDS:
            return False, "Racine de recherche inconnue.", [], False
        if not base.get_root_permissions(root).get("enabled", False):
            continue

        root_path, error = _root_path(root)
        if root_path is None:
            continue

        stack = [(root_path, 0)]

        while stack:
            current, depth = stack.pop()
            if depth > max_depth:
                continue

            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        scanned += 1
                        if scanned > max_entries:
                            limit_reached = True
                            stack.clear()
                            break

                        path = Path(entry.path)

                        try:
                            if base.is_hard_protected_path(path):
                                continue
                            if base.is_reparse_point(path):
                                continue
                            if base.is_hidden_or_system(path):
                                continue

                            is_dir = entry.is_dir(follow_symlinks=False)
                            is_file = entry.is_file(follow_symlinks=False)
                        except OSError:
                            continue

                        if entry.name.casefold() == wanted:
                            type_ok = (
                                item_type == "any"
                                or (item_type == "file" and is_file)
                                or (item_type == "dir" and is_dir)
                            )
                            if type_ok:
                                matches.append((root, path))
                                if len(matches) >= max_results:
                                    limit_reached = True
                                    stack.clear()
                                    break

                        if is_dir and depth < max_depth:
                            stack.append((path, depth + 1))

            except (OSError, PermissionError):
                continue

            if limit_reached:
                break

        if limit_reached:
            break

    return True, None, matches, limit_reached


def find_filesystem_item(name, root_name=None, item_type="any", explicit_user_command=False, source="manual"):
    policy = get_recursive_access_policy()
    ok, error = _manual_policy_check(
        policy,
        explicit_user_command,
        source,
        "La recherche de fichiers",
    )
    if not ok:
        return False, error

    if item_type == "file":
        success, error, matches, limited, _ = _search_file_reference(
            name,
            root_name=root_name,
        )
    else:
        success, error, matches, limited = _search_exact(name, root_name, item_type)
        if success and not matches and item_type == "any":
            # Pour une recherche non typée, un fichier peut être désigné sans
            # extension ou par un fragment de son nom. Les dossiers restent
            # volontairement sur une correspondance exacte.
            file_success, file_error, file_matches, file_limited, _ = _search_file_reference(
                name,
                root_name=root_name,
            )
            if not file_success:
                return False, file_error
            matches = file_matches
            limited = file_limited

    if not success:
        return False, error

    if not matches:
        suffix = " La limite de recherche a été atteinte." if limited else ""
        where = f" dans {base.DISPLAY_NAMES.get(root_name, root_name)}" if root_name else ""
        return False, f"Aucun élément correspondant à '{name}' n'a été trouvé{where}.{suffix}"

    lines = [f"Élément(s) nommé(s) '{name}' trouvé(s) :"]
    for root, path in matches:
        kind = "dossier" if path.is_dir() else "fichier"
        lines.append(f"- [{kind}] {relative_display(root, path)}")

    if limited:
        lines.append("- Recherche arrêtée à la limite de sécurité configurée.")

    return True, "\n".join(lines)


def get_unique_reference_for_context(name, root_name=None, item_type="any"):
    """Résout une référence unique sans lire son contenu.

    Cette fonction est destinée aux actions déjà validées par AgentLocal
    (mémoire de session / copie contrôlée de chemin). Elle ne choisit jamais
    entre plusieurs résultats.
    """
    item_type = str(item_type or "any").strip().lower()
    if item_type not in {"any", "file", "dir"}:
        return False, "Type de référence invalide."

    if root_name is not None:
        root_name = str(root_name).strip().lower()
        root, error = _root_path(root_name)
        if root is None:
            return False, error

    if item_type == "file":
        success, error, matches, limited, _ = _search_file_reference(name, root_name=root_name)
    else:
        success, error, matches, limited = _search_exact(name, root_name, item_type)
        if success and not matches and item_type == "any":
            success, error, matches, limited, _ = _search_file_reference(name, root_name=root_name)

    if not success:
        return False, error
    if not matches:
        suffix = " La limite de recherche a été atteinte." if limited else ""
        return False, f"Aucune référence unique correspondant à '{name}' n'a été trouvée.{suffix}"
    if len(matches) != 1:
        locations = ", ".join(relative_display(root, path) for root, path in matches[:10])
        return False, (
            f"Plusieurs éléments correspondent à '{name}' : {locations}. "
            "Précise la racine ou le chemin."
        )

    root_name_found, path = matches[0]
    root_path, error = _root_path(root_name_found)
    if root_path is None:
        return False, error
    try:
        relative_path = str(path.resolve(strict=True).relative_to(root_path.resolve(strict=True)))
    except (OSError, RuntimeError, ValueError):
        return False, "Impossible de vérifier la référence trouvée."

    return True, {
        "root_name": root_name_found,
        "relative_path": relative_path,
        "item_type": "dir" if path.is_dir() else "file",
    }


def _unique_directory_candidate(directory_name, root_name=None):
    success, error, matches, limited = _search_exact(directory_name, root_name, "dir")
    if not success:
        return False, error
    if not matches:
        suffix = " La limite de recherche a été atteinte." if limited else ""
        return False, f"Aucun dossier nommé '{directory_name}' n'a été trouvé.{suffix}"
    if len(matches) != 1:
        locations = ", ".join(relative_display(root, path) for root, path in matches[:10])
        return False, (
            f"Plusieurs dossiers nommés '{directory_name}' ont été trouvés : {locations}. "
            "Précise la racine ou le chemin."
        )
    return True, matches[0]


# ============================================================
# LISTING RECURSIF CIBLE
# ============================================================

def list_directory(root_name, relative_path=None, explicit_user_command=False, source="manual"):
    relative_path = "" if relative_path is None else str(relative_path).strip()

    if not relative_path:
        return base.list_directory(root_name)

    if not base.has_root_permission(root_name, "can_list"):
        return False, "La consultation de ce dossier n'est pas autorisée."

    policy = get_recursive_access_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La consultation du sous-dossier")
    if not ok:
        return False, error

    ok, directory = resolve_existing_directory(root_name, relative_path)
    if not ok:
        return False, directory

    try:
        entries = list(directory.iterdir())
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de consulter le dossier : {exc}"

    visible = []
    protected_count = 0

    for item in entries:
        try:
            if base.is_hard_protected_path(item) or base.is_reparse_point(item) or base.is_hidden_or_system(item):
                protected_count += 1
                continue
            visible.append(item)
        except OSError:
            protected_count += 1

    visible.sort(key=lambda p: (not p.is_dir(), p.name.casefold()))
    title = relative_display(root_name, directory)

    if not visible:
        message = f"{title} est vide."
        if protected_count:
            message += f" {protected_count} élément(s) protégé(s) ont été ignorés."
        return True, message

    lines = [f"Contenu de {title} :"]
    metadata_allowed = base.has_root_permission(root_name, "can_read_metadata")

    for item in visible:
        try:
            item_type = "dossier" if item.is_dir() else "fichier" if item.is_file() else "élément"
            line = f"- [{item_type}] {item.name}"
            if item_type == "fichier":
                if base.is_blocked_file_type(item.name):
                    line += " | protégé"
                else:
                    category = base.get_media_category(item.name)
                    if category:
                        line += f" | {category}"
            if metadata_allowed:
                try:
                    stat = item.stat(follow_symlinks=False)
                    if item_type == "fichier":
                        line += f" | {base.format_size(stat.st_size)}"
                except OSError:
                    pass
            lines.append(line)
        except OSError:
            continue

    if protected_count:
        lines.append(f"\n{protected_count} élément(s) protégé(s) ont été ignorés.")

    return True, "\n".join(lines)


def list_directory_auto(directory_name, explicit_user_command=False, source="manual"):
    policy = get_recursive_access_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La recherche de dossier")
    if not ok:
        return False, error
    ok, candidate = _unique_directory_candidate(directory_name)
    if not ok:
        return False, candidate
    root, path = candidate
    root_path, _ = _root_path(root)
    rel = str(path.relative_to(root_path))
    return list_directory(root, rel, explicit_user_command=True, source="manual")


# ============================================================
# CREATION D'UN DOSSIER DANS UN SOUS-DOSSIER
# ============================================================

def create_folder(root_name, folder_name, explicit_user_command=False):
    # Compatibilité : nom simple à la racine -> ancienne fonction validée.
    if isinstance(folder_name, str) and "\\" not in folder_name and "/" not in folder_name:
        return base.create_folder(root_name, folder_name, explicit_user_command=explicit_user_command)

    if not base.has_root_permission(root_name, "can_create_folder"):
        return False, f"La création de dossiers n'est pas autorisée dans {base.DISPLAY_NAMES.get(root_name, root_name)}."

    policy = base.get_creation_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "La création d'un dossier")
    if not ok:
        return False, error

    ok, target = resolve_new_leaf_inside_root(root_name, folder_name, leaf_kind="dir")
    if not ok:
        return False, target

    try:
        target.mkdir(parents=False, exist_ok=False)
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de créer le dossier : {exc}"

    return True, f"Le dossier '{relative_display(root_name, target)}' a été créé."


# ============================================================
# LECTURE MULTIFORMAT DANS LES SOUS-DOSSIERS
# ============================================================

def _extract_read_content(resolved_source, extension, policy, maximum_file_size, maximum_output):
    if extension in base.PLAIN_TEXT_READ_EXTENSIONS:
        return base.extract_plain_text_content(resolved_source, maximum_file_size, maximum_output)
    if extension in base.HTML_READ_EXTENSIONS:
        return base.extract_html_file_content(resolved_source, maximum_file_size, maximum_output)
    if extension in base.RTF_READ_EXTENSIONS:
        return base.extract_rtf_file_content(resolved_source, maximum_file_size, maximum_output)
    if extension == ".docx":
        return base.extract_docx_content(resolved_source, policy, maximum_output)
    if extension == ".xlsx":
        return base.extract_xlsx_content(resolved_source, policy, maximum_output)
    if extension == ".pptx":
        return base.extract_pptx_content(resolved_source, policy, maximum_output)
    if extension in base.OPEN_DOCUMENT_READ_EXTENSIONS:
        return base.extract_open_document_content(resolved_source, extension, policy, maximum_output)
    if extension in base.EPUB_READ_EXTENSIONS:
        return base.extract_epub_content(resolved_source, policy, maximum_output)
    if extension in base.EMAIL_READ_EXTENSIONS:
        return base.extract_eml_content(resolved_source, maximum_output)
    if extension in base.PDF_READ_EXTENSIONS:
        return base.extract_pdf_content(resolved_source, policy, maximum_output)
    return False, "Le format demandé n'a aucun lecteur local autorisé.", "", False


def read_file_content(root_name, file_name, explicit_user_command=False, source="unspecified"):
    if not base.has_filesystem_permission("can_read_content"):
        return False, "La lecture du contenu des fichiers est désactivée."
    if not base.has_root_permission(root_name, "can_read_content"):
        return False, "La lecture du contenu n'est pas autorisée dans cette racine."

    policy = base.get_read_content_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La lecture d'un fichier")
    if not ok:
        return False, error

    ok, source_path = resolve_file_reference_inside_root(root_name, file_name)
    if not ok:
        return False, source_path

    extension = source_path.suffix.lower()
    allowed_extensions = base.get_allowed_read_extensions()
    if extension not in allowed_extensions:
        if extension in base.HARD_BLOCKED_DOCUMENT_READ_EXTENSIONS:
            return False, f"Le format '{extension}' reste volontairement bloqué."
        return False, f"Le type de fichier '{extension or '(sans extension)'}' n'est pas autorisé pour la lecture."

    try:
        stats = source_path.stat(follow_symlinks=False)
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de lire les métadonnées du fichier : {exc}"

    maximum_file_size = base.get_positive_read_limit(
        policy,
        "maximum_file_size_bytes",
        base.HARD_MAX_READ_FILE_BYTES,
    )
    maximum_output = base.get_positive_read_limit(
        policy,
        "maximum_output_characters",
        base.HARD_MAX_READ_OUTPUT_CHARACTERS,
    )
    if maximum_file_size is None or maximum_output is None:
        return False, "Une limite de lecture est invalide."
    if stats.st_size > maximum_file_size:
        return False, (
            f"Le fichier est trop volumineux ({base.format_size(stats.st_size)}). "
            f"Limite : {base.format_size(maximum_file_size)}."
        )

    success, content, format_name, truncated = _extract_read_content(
        source_path,
        extension,
        policy,
        maximum_file_size,
        maximum_output,
    )
    if not success:
        return False, content if content else format_name

    header = f"Contenu de '{relative_display(root_name, source_path)}' (format : {format_name}) :"
    message = header + "\n\n" + (content or "[Document vide ou sans texte extractible]")
    if truncated:
        message += "\n\n[Contenu tronqué : une limite de sécurité ou de sortie a été atteinte.]"
    return True, message


def read_file_auto(file_name, explicit_user_command=False, source="manual"):
    policy = base.get_read_content_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La lecture automatique localisée")
    if not ok:
        return False, error
    ok, candidate = _unique_file_candidate(file_name)
    if not ok:
        return False, candidate
    root, path = candidate
    root_path, _ = _root_path(root)
    rel = str(path.relative_to(root_path))
    return read_file_content(root, rel, explicit_user_command=True, source="manual")


# ============================================================
# CREATION DE FICHIER DANS UN SOUS-DOSSIER
# ============================================================

def create_file_with_content(root_name, file_name, content, explicit_user_command=False, source="unspecified"):
    if isinstance(file_name, str) and "\\" not in file_name and "/" not in file_name:
        return base.create_file_with_content(
            root_name,
            file_name,
            content,
            explicit_user_command=explicit_user_command,
            source=source,
        )

    if not base.has_filesystem_permission("can_write_content"):
        return False, "La création de fichiers avec contenu est désactivée."
    if not base.has_root_permission(root_name, "can_create_file"):
        return False, "La création de fichiers n'est pas autorisée dans cette racine."

    policy = base.get_create_file_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La création du fichier")
    if not ok:
        return False, error
    if policy.get("allow_overwrite", False):
        return False, "La configuration d'écrasement est refusée par AgentLocal."

    ok, destination_path = resolve_new_leaf_inside_root(root_name, file_name, leaf_kind="file")
    if not ok:
        return False, destination_path

    extension = destination_path.suffix.lower()
    if extension not in base.get_allowed_create_file_extensions():
        return False, f"L'extension '{extension or '(aucune)'}' n'est pas autorisée pour la création."

    if not isinstance(content, str) or "\x00" in content:
        return False, "Le contenu du fichier est invalide ou binaire."

    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError:
        return False, "Le contenu ne peut pas être encodé en UTF-8."

    try:
        maximum = int(policy.get("maximum_content_bytes", 0))
    except (TypeError, ValueError):
        return False, "La limite de taille d'écriture est invalide."

    if maximum <= 0 or maximum > base.HARD_MAX_CREATE_FILE_CONTENT_BYTES:
        return False, "La limite de taille d'écriture est invalide ou trop élevée."
    if len(encoded) > maximum:
        return False, f"Le contenu est trop volumineux. Limite : {base.format_size(maximum)}."

    fd = None
    try:
        fd = os.open(str(destination_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            fd = None
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return False, "Le fichier existe déjà. Aucun écrasement n'est autorisé."
    except (OSError, PermissionError) as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        return False, f"Impossible de créer le fichier : {exc}"

    return True, f"Le fichier '{relative_display(root_name, destination_path)}' a été créé."


# ============================================================
# MODIFICATION D'UN FICHIER DANS UN SOUS-DOSSIER
# ============================================================

def modify_file_content(root_name, file_name, content, mode, explicit_user_command=False, source="unspecified"):
    if not base.has_filesystem_permission("can_write_content") or not base.has_filesystem_permission("can_modify_content"):
        return False, "La modification du contenu des fichiers est désactivée."
    if not base.has_root_permission(root_name, "can_modify_file"):
        return False, "La modification de fichiers n'est pas autorisée dans cette racine."

    policy = base.get_modify_file_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La modification du fichier")
    if not ok:
        return False, error

    mode = str(mode).strip().lower()
    allowed_modes = {str(item).strip().lower() for item in policy.get("allowed_modes", []) if isinstance(item, str)}
    if mode not in {"replace_content", "append_content", "append_line"} or mode not in allowed_modes:
        return False, "Mode de modification interdit ou inconnu."

    ok, source_path = resolve_file_reference_inside_root(root_name, file_name)
    if not ok:
        return False, source_path

    extension = source_path.suffix.lower()
    if extension not in base.get_allowed_modify_file_extensions():
        return False, f"L'extension '{extension or '(aucune)'}' n'est pas autorisée pour la modification."
    if mode in {"append_content", "append_line"} and extension not in base.get_append_safe_modify_extensions():
        return False, "L'ajout à la fin est limité aux formats textuels simples."

    if not isinstance(content, str) or "\x00" in content:
        return False, "Le nouveau contenu est invalide ou binaire."
    if mode == "append_line" and ("\n" in content or "\r" in content):
        return False, "Le mode 'ajoute une ligne' accepte une seule ligne de texte."

    def limit(key, hard):
        try:
            value = int(policy.get(key, 0))
        except (TypeError, ValueError):
            return None
        return value if 0 < value <= hard else None

    maximum_existing = limit("maximum_existing_file_bytes", base.HARD_MAX_MODIFY_EXISTING_BYTES)
    maximum_added = limit("maximum_added_content_bytes", base.HARD_MAX_MODIFY_ADDED_BYTES)
    maximum_result = limit("maximum_result_bytes", base.HARD_MAX_MODIFY_RESULT_BYTES)
    if None in {maximum_existing, maximum_added, maximum_result}:
        return False, "Une limite de taille de modification est invalide."

    try:
        requested_utf8 = content.encode("utf-8")
    except UnicodeEncodeError:
        return False, "Le contenu demandé n'est pas un texte Unicode valide."
    if len(requested_utf8) > maximum_added:
        return False, f"Le contenu demandé est trop volumineux. Limite : {base.format_size(maximum_added)}."

    original_fingerprint = base.get_file_fingerprint(source_path)
    if original_fingerprint is None:
        return False, "Impossible d'obtenir l'empreinte du fichier."
    if original_fingerprint[0] > maximum_existing:
        return False, f"Le fichier est trop volumineux. Limite : {base.format_size(maximum_existing)}."

    try:
        with open(source_path, "rb") as handle:
            original_bytes = handle.read(maximum_existing + 1)
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de lire le fichier avant modification : {exc}"

    if len(original_bytes) > maximum_existing or base.looks_like_binary_data(original_bytes):
        return False, "Le fichier est trop volumineux ou ressemble à un contenu binaire."
    if base.get_file_fingerprint(source_path) != original_fingerprint:
        return False, "Le fichier a changé pendant sa lecture. La modification est annulée."

    ok, original_text, detected_encoding = base.decode_text_bytes_for_modification(original_bytes)
    if not ok:
        return False, original_text

    if mode == "replace_content":
        result_text = content
    elif mode == "append_content":
        result_text = original_text + content
    else:
        newline = "\r\n" if "\r\n" in original_text else "\n"
        if not original_text:
            result_text = content
        elif original_text.endswith(("\n", "\r")):
            result_text = original_text + content
        else:
            result_text = original_text + newline + content

    try:
        result_bytes = result_text.encode(detected_encoding, errors="strict")
    except UnicodeEncodeError:
        return False, f"Le nouveau contenu ne peut pas être enregistré en '{detected_encoding}' sans perte."
    if len(result_bytes) > maximum_result:
        return False, f"Le résultat serait trop volumineux. Limite : {base.format_size(maximum_result)}."

    success, error = base.write_existing_file_atomically(source_path, result_bytes, original_fingerprint)
    if not success:
        return False, error

    labels = {
        "replace_content": "contenu remplacé",
        "append_content": "contenu ajouté",
        "append_line": "ligne ajoutée",
    }
    return True, f"Le fichier '{relative_display(root_name, source_path)}' a été modifié ({labels[mode]})."


# ============================================================
# RENOMMAGE DANS LES SOUS-DOSSIERS
# ============================================================

def rename_file(root_name, old_name, new_name, explicit_user_command=False):
    if not base.has_filesystem_permission("can_rename") or not base.has_root_permission(root_name, "can_rename"):
        return False, "Le renommage n'est pas autorisé dans cette racine."

    policy = base.get_rename_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "Le renommage")
    if not ok:
        return False, error

    ok, source_path = resolve_file_reference_inside_root(root_name, old_name)
    if not ok:
        return False, source_path

    valid_new, validated_new = _resolved_rename_destination_name(
        source_path,
        new_name,
    )
    if not valid_new:
        return False, validated_new

    old_leaf = source_path.name
    if old_leaf.casefold() == validated_new.casefold():
        return False, "L'ancien et le nouveau nom ne peuvent pas être identiques ou différer uniquement par la casse."

    if not policy.get("allow_extension_change", False):
        if base.get_extension_chain(old_leaf) != base.get_extension_chain(validated_new):
            return False, "Le changement d'extension est interdit."

    destination = source_path.parent / validated_new
    if os.path.lexists(str(destination)):
        return False, f"'{validated_new}' existe déjà. Aucun écrasement n'est autorisé."

    try:
        os.rename(source_path, destination)
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de renommer le fichier : {exc}"

    return True, f"Le fichier '{relative_display(root_name, source_path)}' a été renommé en '{validated_new}'."


def rename_file_auto(old_name, new_name, explicit_user_command=False):
    policy = base.get_rename_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "Le renommage automatique localisé")
    if not ok:
        return False, error
    if not policy.get("allow_auto_root_discovery", False):
        return False, "La localisation automatique pour le renommage est désactivée."

    valid_old, cleaned_old = _validate_file_reference(old_name)
    if not valid_old:
        return False, cleaned_old
    valid_new, cleaned_new = base.validate_file_name(new_name)
    if not valid_new:
        return False, cleaned_new

    ok, candidate = _unique_file_candidate(cleaned_old)
    if not ok:
        return False, candidate

    root, path = candidate
    root_path, _ = _root_path(root)
    rel = str(path.relative_to(root_path))
    return rename_file(root, rel, cleaned_new, explicit_user_command=True)


# ============================================================
# SUPPRESSION VERS CORBEILLE DANS LES SOUS-DOSSIERS
# ============================================================

def delete_file_to_recycle_bin(root_name, file_name, explicit_user_command=False):
    if not base.has_filesystem_permission("can_delete") or not base.has_root_permission(root_name, "can_delete"):
        return False, "La suppression contrôlée n'est pas autorisée dans cette racine."

    policy = base.get_delete_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "La suppression")
    if not ok:
        return False, error
    if str(policy.get("mode", "")).strip().lower() != "recycle_bin_only":
        return False, "Seule la Corbeille Windows est autorisée."
    if policy.get("allow_permanent_delete", False):
        return False, "La suppression définitive reste interdite."

    ok, source_path = resolve_file_reference_inside_root(root_name, file_name)
    if not ok:
        return False, source_path
    if base.is_blocked_file_type(source_path.name):
        return False, "Ce type de fichier protégé ne peut pas être supprimé par AgentLocal."

    success, error = base.send_file_to_recycle_bin(source_path)
    if not success:
        return False, error
    return True, f"Le fichier '{relative_display(root_name, source_path)}' a été envoyé dans la Corbeille Windows."


def delete_file_auto(file_name, explicit_user_command=False):
    policy = base.get_delete_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "La suppression automatiquement localisée")
    if not ok:
        return False, error
    ok, candidate = _unique_file_candidate(file_name)
    if not ok:
        return False, candidate
    root, path = candidate
    root_path, _ = _root_path(root)
    rel = str(path.relative_to(root_path))
    return delete_file_to_recycle_bin(root, rel, explicit_user_command=True)


# ============================================================
# COPIE ENTRE RACINES / SOUS-DOSSIERS
# ============================================================

def copy_file_between_roots(
    source_root,
    destination_root,
    file_name,
    destination_folder_name=None,
    explicit_user_command=False,
    source="unspecified",
):
    simple_source = isinstance(file_name, str) and "\\" not in file_name and "/" not in file_name
    simple_destination = destination_folder_name in {None, ""} or (
        isinstance(destination_folder_name, str)
        and "\\" not in destination_folder_name
        and "/" not in destination_folder_name
    )
    exact_source_ok, _ = resolve_existing_inside_root(
        source_root,
        file_name,
        expected="file",
    )
    if simple_source and simple_destination and exact_source_ok:
        return base.copy_file_between_roots(
            source_root,
            destination_root,
            file_name,
            destination_folder_name=destination_folder_name,
            explicit_user_command=explicit_user_command,
            source=source,
        )

    if not base.has_filesystem_permission("can_copy"):
        return False, "La copie de fichiers est désactivée."
    if not base.has_root_permission(source_root, "can_copy_out"):
        return False, "La copie depuis la racine source n'est pas autorisée."
    if not base.has_root_permission(destination_root, "can_receive_copy"):
        return False, "La copie vers la racine destination n'est pas autorisée."

    policy = base.get_copy_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, source, "La copie")
    if not ok:
        return False, error

    ok, source_path = resolve_file_reference_inside_root(source_root, file_name)
    if not ok:
        return False, source_path
    if base.is_blocked_file_type(source_path.name):
        return False, "Ce type de fichier protégé ne peut pas être copié."

    destination_folder_name = "" if destination_folder_name is None else str(destination_folder_name).strip()
    ok, destination_folder = resolve_existing_directory(destination_root, destination_folder_name)
    if not ok:
        return False, destination_folder

    destination_path = destination_folder / source_path.name
    if os.path.lexists(str(destination_path)):
        return False, "Un fichier du même nom existe déjà dans la destination."

    source_fingerprint = base.get_file_fingerprint(source_path)
    if source_fingerprint is None:
        return False, "Impossible de vérifier le fichier source avant copie."

    fd = None
    try:
        fd = os.open(str(destination_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with open(source_path, "rb") as source_handle, os.fdopen(fd, "wb") as destination_handle:
            fd = None
            while True:
                chunk = source_handle.read(1024 * 1024)
                if not chunk:
                    break
                destination_handle.write(chunk)
            destination_handle.flush()
            os.fsync(destination_handle.fileno())
        try:
            shutil.copystat(source_path, destination_path, follow_symlinks=False)
        except OSError:
            pass
    except (OSError, PermissionError) as exc:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            if destination_path.exists():
                destination_path.unlink()
        except OSError:
            pass
        return False, f"Impossible de copier le fichier : {exc}"

    if base.get_file_fingerprint(source_path) != source_fingerprint:
        try:
            destination_path.unlink()
        except OSError:
            pass
        return False, "Le fichier source a changé pendant la copie. La copie a été annulée."

    return True, (
        f"Le fichier '{relative_display(source_root, source_path)}' a été copié vers "
        f"'{relative_display(destination_root, destination_path)}'."
    )


# ============================================================
# DEPLACEMENT DANS / ENTRE SOUS-DOSSIERS
# ============================================================

def move_file_within_root(root_name, file_name, destination_folder_name, explicit_user_command=False):
    simple_source = isinstance(file_name, str) and "\\" not in file_name and "/" not in file_name
    simple_destination = isinstance(destination_folder_name, str) and "\\" not in destination_folder_name and "/" not in destination_folder_name
    exact_source_ok, _ = resolve_existing_inside_root(
        root_name,
        file_name,
        expected="file",
    )
    if simple_source and simple_destination and exact_source_ok:
        return base.move_file_within_root(
            root_name,
            file_name,
            destination_folder_name,
            explicit_user_command=explicit_user_command,
        )

    if not base.has_root_permission(root_name, "can_move_within_root"):
        return False, "Le déplacement interne n'est pas autorisé dans cette racine."
    policy = base.get_move_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "Le déplacement")
    if not ok:
        return False, error

    ok, source_path = resolve_file_reference_inside_root(root_name, file_name)
    if not ok:
        return False, source_path
    ok, destination_folder = resolve_existing_directory(root_name, destination_folder_name)
    if not ok:
        return False, destination_folder

    destination_path = destination_folder / source_path.name
    if base.is_same_path(source_path.parent, destination_folder):
        return False, "Le fichier se trouve déjà dans ce dossier."
    if os.path.lexists(str(destination_path)):
        return False, "Un fichier du même nom existe déjà dans la destination."

    try:
        os.rename(source_path, destination_path)
    except (OSError, PermissionError) as exc:
        return False, f"Impossible de déplacer le fichier : {exc}"

    return True, f"Le fichier a été déplacé vers '{relative_display(root_name, destination_path)}'."


def move_file_between_roots(
    source_root,
    destination_root,
    file_name,
    destination_folder_name=None,
    explicit_user_command=False,
):
    simple_source = isinstance(file_name, str) and "\\" not in file_name and "/" not in file_name
    simple_destination = destination_folder_name in {None, ""} or (
        isinstance(destination_folder_name, str)
        and "\\" not in destination_folder_name
        and "/" not in destination_folder_name
    )
    exact_source_ok, _ = resolve_existing_inside_root(
        source_root,
        file_name,
        expected="file",
    )
    if simple_source and simple_destination and exact_source_ok:
        return base.move_file_between_roots(
            source_root,
            destination_root,
            file_name,
            destination_folder_name=destination_folder_name,
            explicit_user_command=explicit_user_command,
        )

    if str(source_root).strip().lower() == str(destination_root).strip().lower():
        return move_file_within_root(
            source_root,
            file_name,
            destination_folder_name or "",
            explicit_user_command=explicit_user_command,
        )

    policy = base.get_cross_root_move_policy()
    ok, error = _manual_policy_check(policy, explicit_user_command, "manual", "Le déplacement entre racines")
    if not ok:
        return False, error
    if not base.is_cross_root_transfer_allowed(source_root, destination_root):
        return False, "Ce transfert entre racines n'est pas autorisé."

    ok, source_path = resolve_file_reference_inside_root(source_root, file_name)
    if not ok:
        return False, source_path
    ok, destination_folder = resolve_existing_directory(destination_root, destination_folder_name or "")
    if not ok:
        return False, destination_folder

    destination_path = destination_folder / source_path.name
    if os.path.lexists(str(destination_path)):
        return False, "Un fichier du même nom existe déjà dans la destination."

    try:
        os.rename(source_path, destination_path)
    except OSError as exc:
        return False, (
            "Impossible de déplacer le fichier. Aucune copie+suppression automatique n'est utilisée. "
            f"Détail : {exc}"
        )

    return True, (
        f"Le fichier '{relative_display(source_root, source_path)}' a été déplacé vers "
        f"'{relative_display(destination_root, destination_path)}'."
    )
