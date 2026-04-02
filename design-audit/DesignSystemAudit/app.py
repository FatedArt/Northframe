import re
import math
import os
import json
from datetime import datetime
from pathlib import Path
from collections import Counter

import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

FIGMA_API = "https://api.figma.com/v1"
# Monorepo root (Northframe/) — export audit markdown ke folder Research/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE = REPO_ROOT / "Research"

VISUAL_COLOR_WORDS = {
    "red", "green", "blue", "yellow", "orange", "purple", "pink", "cyan",
    "teal", "gray", "grey", "black", "white", "brown", "violet", "indigo",
    "lime", "amber", "magenta", "slate", "zinc", "stone", "neutral",
}

def is_folder_component_frame_name(name: str) -> bool:
    return isinstance(name, str) and name.startswith("Folder:")

def node_is_in_folder_component_frame(node: dict) -> bool:
    frame_path = node.get("frame_path") or ""
    segments = [s.strip() for s in frame_path.split("/") if s.strip()]
    return any(is_folder_component_frame_name(seg) for seg in segments)

def filter_nodes_folder_only(flat_nodes: list) -> list:
    return [n for n in (flat_nodes or []) if node_is_in_folder_component_frame(n)]

def filter_meta_by_scoped_ids(meta: dict, scoped_ids: set) -> dict:
    return {k: v for k, v in (meta or {}).items() if k in scoped_ids}

# ─── Figma URL parsing ───────────────────────────────────────────────

def parse_figma_url(url: str) -> dict:
    m = re.search(r"figma\.com/(?:file|design)/([A-Za-z0-9]+)", url)
    file_key = m.group(1) if m else None
    node_id = None
    nm = re.search(r"node-id=([0-9]+-[0-9]+)", url)
    if nm:
        node_id = nm.group(1).replace("-", ":")
    return {"file_key": file_key, "node_id": node_id}


# ─── Figma REST API helpers ──────────────────────────────────────────

def figma_get(endpoint: str, token: str, params: dict | None = None):
    headers = {"X-Figma-Token": token}
    r = requests.get(f"{FIGMA_API}{endpoint}", headers=headers, params=params or {}, timeout=60)
    r.raise_for_status()
    return r.json()


def fetch_file(file_key: str, token: str, node_id: str | None = None, depth: int = 4):
    params = {"depth": depth}
    if node_id:
        params["ids"] = node_id
    return figma_get(f"/files/{file_key}", token, params)


def fetch_variables(file_key: str, token: str, strict: bool = False):
    try:
        data = figma_get(f"/files/{file_key}/variables/local", token)
        print(f"[Variables API] OK — {len((data.get('meta') or {}).get('variables') or {})} variables, {len((data.get('meta') or {}).get('variableCollections') or {})} collections")
        return data
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 0
        body = ""
        try:
            body = (e.response.text or "")[:260] if e.response is not None else ""
        except Exception:
            body = ""
        print(f"[Variables API] HTTP {status} — token mungkin tidak punya scope 'file_variables:read' | body: {body}")
        if strict and status == 403:
            raise PermissionError(f"Variables API 403 dari Figma. Detail: {body or 'Forbidden'}")
        return {}
    except Exception as e:
        print(f"[Variables API] Error: {e}")
        if strict:
            raise
        return {}


# ─── Node tree utilities ─────────────────────────────────────────────

def walk_tree(node, parent=None, frame_path="", depth=0):
    if not node or not isinstance(node, dict):
        return []

    current_path = frame_path
    if node.get("type") in ("FRAME", "SECTION", "COMPONENT_SET", "PAGE", "CANVAS"):
        current_path = f"{frame_path}/{node.get('name', '')}" if frame_path else node.get("name", "")

    bbox = node.get("absoluteBoundingBox") or {}
    style = node.get("style") or {}
    styles = node.get("styles") or {}
    bound_vars = node.get("boundVariables") or {}
    comp_props = node.get("componentPropertyDefinitions") or {}

    entry = {
        "id": node.get("id"),
        "name": node.get("name") or "",
        "type": node.get("type") or "",
        "parent_id": parent.get("id") if parent else None,
        "parent_name": parent.get("name") if parent else None,
        "frame_path": current_path,
        "fills": node.get("fills") or [],
        "strokes": node.get("strokes") or [],
        "bound_variables": bound_vars,
        "component_properties": comp_props,
        "description": node.get("description") or "",
        "width": bbox.get("width", 0) if isinstance(bbox, dict) else 0,
        "height": bbox.get("height", 0) if isinstance(bbox, dict) else 0,
        "font_size": style.get("fontSize", 0) if isinstance(style, dict) else 0,
        "line_height_px": style.get("lineHeightPx") if isinstance(style, dict) else None,
        "text_style_id": styles.get("text") if isinstance(styles, dict) else None,
        "fill_style_id": (styles.get("fill") or styles.get("fills")) if isinstance(styles, dict) else None,
        "effect_style_id": styles.get("effect") if isinstance(styles, dict) else None,
        "characters": node.get("characters") or "",
        "depth": depth,
    }

    result = [entry]
    for child in (node.get("children") or []):
        result.extend(walk_tree(child, parent=node, frame_path=current_path, depth=depth + 1))
    return result


# ─── Color utilities ─────────────────────────────────────────────────

def figma_rgba_to_hex(c):
    if not c or not isinstance(c, dict):
        return None
    r = int(c.get("r", 0) * 255)
    g = int(c.get("g", 0) * 255)
    b = int(c.get("b", 0) * 255)
    return f"#{r:02X}{g:02X}{b:02X}"


def relative_luminance(r, g, b):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast_ratio(fg, bg):
    l1 = relative_luminance(*fg)
    l2 = relative_luminance(*bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


# ─── Variable helpers ─────────────────────────────────────────────────

def is_visual_name(name: str) -> bool:
    parts = re.split(r"[/\-_.\s]+", name.lower())
    return any(p in VISUAL_COLOR_WORDS for p in parts)


def organize_tokens(variables_data):
    meta = variables_data.get("meta") or {}
    var_map = meta.get("variables") or {}
    col_map = meta.get("variableCollections") or {}

    print(f"[Tokens] var_map keys: {len(var_map)}, col_map keys: {len(col_map)}")
    if var_map:
        sample_key = next(iter(var_map))
        print(f"[Tokens] Sample var key: {sample_key}")
    if col_map:
        sample_col = next(iter(col_map.values()))
        sample_ids = (sample_col.get("variableIds") or [])[:2]
        print(f"[Tokens] Sample collection variableIds: {sample_ids}")

    summary = {"colors": 0, "numbers": 0, "strings": 0, "booleans": 0}
    collections = []

    for col_id, col in col_map.items():
        modes = col.get("modes") or []
        first_mode_id = modes[0].get("modeId") if modes else None
        var_ids = col.get("variableIds") or []
        if not var_ids:
            # Fallback: some responses rely on variableCollectionId linkage.
            var_ids = [vid for vid, v in var_map.items() if v.get("variableCollectionId") == col_id]

        groups = {}
        matched = 0
        for vid in var_ids:
            var = var_map.get(vid)
            if not var:
                # Fallback when variableIds and map keys use different shapes.
                var = next((v for v in var_map.values() if v.get("id") == vid), None)
            if not var:
                continue
            matched += 1

            resolved = var.get("resolvedType", "")
            name = var.get("name", "")
            name_parts = name.rsplit("/", 1)
            group_name = name_parts[0].upper() if len(name_parts) > 1 else col.get("name", "").upper()
            short_name = name_parts[-1] if len(name_parts) > 1 else name

            value_raw = None
            hex_val = None
            if first_mode_id and var.get("valuesByMode"):
                value_raw = var["valuesByMode"].get(first_mode_id)

            if resolved == "COLOR" and isinstance(value_raw, dict):
                hex_val = figma_rgba_to_hex(value_raw)
                summary["colors"] += 1
            elif resolved == "FLOAT":
                summary["numbers"] += 1
            elif resolved == "STRING":
                summary["strings"] += 1
            elif resolved == "BOOLEAN":
                summary["booleans"] += 1

            is_alias = isinstance(value_raw, dict) and value_raw.get("type") == "VARIABLE_ALIAS"

            token_entry = {
                "id": vid,
                "name": short_name,
                "full_name": name,
                "type": resolved,
                "hex": hex_val,
                "value": str(value_raw) if not isinstance(value_raw, dict) else hex_val or "(alias)",
                "is_alias": is_alias,
            }

            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(token_entry)

        print(f"[Tokens] Collection '{col.get('name', '')}': {len(var_ids)} var_ids, {matched} matched, {len(groups)} groups")

        sorted_groups = []
        for gname in sorted(groups.keys()):
            sorted_groups.append({"name": gname, "tokens": groups[gname]})

        collections.append({
            "id": col_id,
            "name": col.get("name", ""),
            "modes": [{"id": m.get("modeId", ""), "name": m.get("name", "")} for m in modes],
            "groups": sorted_groups,
            "count": matched,
        })

    total = summary["colors"] + summary["numbers"] + summary["strings"] + summary["booleans"]

    return {
        "total": total,
        "summary": summary,
        "collections": collections,
    }


# ─── Audit scorers (enhanced with sub-checks) ─────────────────────────

DEFAULT_NAMES = {
    "Frame", "Group", "Vector", "Rectangle", "Ellipse", "Line",
    "Polygon", "Star", "Boolean", "Slice", "Component", "Instance",
}
DEFAULT_PATTERN = re.compile(r"^(" + "|".join(DEFAULT_NAMES) + r")(\s+\d+)?$", re.I)


def audit_subcheck(label, score, description, icon, examples, explanation, how_to_fix):
    """Satu baris sub-check audit: penjelasan singkat + daftar langkah perbaikan (Bahasa Indonesia)."""
    steps = how_to_fix if isinstance(how_to_fix, list) else [how_to_fix]
    return {
        "label": label,
        "score": score,
        "description": description,
        "icon": icon,
        "examples": examples or [],
        "explanation": explanation,
        "how_to_fix": [s for s in steps if s],
    }


def score_naming(flat_nodes, variables_data):
    subchecks = []

    # 1) Variable naming
    meta = variables_data.get("meta") or {}
    var_map = meta.get("variables") or {}
    color_vars = [v for v in var_map.values() if v.get("resolvedType") == "COLOR"]
    visual_vars = [v for v in color_vars if is_visual_name(v.get("name", ""))]
    var_score = max(0, int(100 * (1 - len(visual_vars) / max(len(color_vars), 1)))) if color_vars else 100

    var_examples = [f"{v.get('name', '')} Color" for v in visual_vars[:5]]
    subchecks.append(audit_subcheck(
        "Variable naming", var_score,
        f"{len(visual_vars)} of {len(color_vars)} color variables use visual names instead of semantic names." if color_vars else "No color variables to evaluate.",
        "warn" if visual_vars else ("info" if not color_vars else "pass"),
        var_examples,
        "Mengecek apakah variabel warna memakai nama yang menjelaskan peran (semantic), bukan nama warna mentah seperti “red/blue”.",
        [
            "Ubah nama variabel ke peran UI: misalnya `color/text/primary`, bukan `color/blue/500`.",
            "Pisahkan primitive (skala warna) dan semantic (teks, border, surface) di collection berbeda.",
            "Gunakan alias: semantic mengarah ke primitive agar tema (light/dark) mudah diubah.",
        ],
    ))

    # 2) Component naming (flat_nodes is already scoped to Folder: frames)
    comp_nodes = [n for n in flat_nodes if n["type"] in ("COMPONENT", "COMPONENT_SET")]
    default_comps = [n for n in comp_nodes if DEFAULT_PATTERN.match(n["name"])]
    comp_score = max(0, int(100 * (1 - len(default_comps) / max(len(comp_nodes), 1)))) if comp_nodes else 100

    subchecks.append(audit_subcheck(
        "Component naming", comp_score,
        f"{len(default_comps)} of {len(comp_nodes)} components use default names." if comp_nodes else "No components to evaluate.",
        "warn" if default_comps else ("info" if not comp_nodes else "pass"),
        [f"{n['name']} ({n['type']}) · id:{n['id']} · {n.get('frame_path','')}" for n in default_comps[:5]],
        "Komponen tidak boleh memakai nama generik Figma (Frame 123, Component) karena sulit dicari dan tidak deskriptif di tim/dev.",
        [
            "Rename layer ke pola yang konsisten: `ComponentName` atau `Category/ComponentName`.",
            "Gunakan nama yang sama dengan yang dipakai di dokumentasi/kode.",
            "Untuk variant, pertahankan nama prop di Component Set yang jelas (mis. Size=sm, md, lg).",
        ],
    ))

    # 3) Variant naming (flat_nodes is already scoped to Folder: frames)
    variant_nodes = [n for n in flat_nodes if n["type"] == "COMPONENT" and "/" in n.get("frame_path", "")]
    bad_variants = [n for n in variant_nodes if DEFAULT_PATTERN.match(n["name"])]
    variant_score = max(0, int(100 * (1 - len(bad_variants) / max(len(variant_nodes), 1)))) if variant_nodes else 100

    subchecks.append(audit_subcheck(
        "Variant naming", variant_score,
        f"{len(bad_variants)} of {len(variant_nodes)} variants use default names." if variant_nodes else "No variant components to evaluate.",
        "warn" if bad_variants else ("info" if not variant_nodes else "pass"),
        [f"{n['name']} · id:{n['id']} · {n.get('frame_path','')}" for n in bad_variants[:5]],
        "Setiap child di dalam Component Set seharusnya punya nama variant yang bermakna, bukan default seperti “Component”.",
        [
            "Buka Component Set, rename tiap variant sesuai kombinasi prop (contoh: `Leading icon`, `Trailing icon`).",
            "Pastikan nama layer variant selaras dengan nilai property di panel kanan.",
        ],
    ))

    # 4) Boolean naming
    bool_props = []
    for n in flat_nodes:
        for pname, pdef in (n.get("component_properties") or {}).items():
            if pdef.get("type") == "BOOLEAN":
                bool_props.append({"name": pname, "node": n["name"]})
    bad_bools = [b for b in bool_props if not any(b["name"].lower().startswith(p) for p in ("is", "has", "show", "with", "enable", "disable", "visible", "hidden"))]
    bool_score = max(0, int(100 * (1 - len(bad_bools) / max(len(bool_props), 1)))) if bool_props else 100

    subchecks.append(audit_subcheck(
        "Boolean naming", bool_score,
        f"{len(bad_bools)} of {len(bool_props)} boolean props lack semantic prefixes (is/has/show/with)." if bool_props else "No boolean properties to evaluate.",
        "warn" if bad_bools else ("info" if not bool_props else "pass"),
        [f"{b['name']} on {b['node']}" for b in bad_bools[:5]],
        "Property boolean yang konsisten memakai awalan seperti `is` / `has` / `show` memudahkan handoff ke kode dan dokumentasi.",
        [
            "Rename property: `visible` → `isVisible`, `icon` → `showIcon`, `disabled` → `isDisabled` (sesuai konvensi tim Anda).",
            "Dokumentasikan konvensi di satu halaman agar semua komponen mengikuti pola yang sama.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


def score_tokens(flat_nodes, variables_data):
    subchecks = []
    meta = variables_data.get("meta") or {}
    col_map = meta.get("variableCollections") or {}
    var_map = meta.get("variables") or {}
    collections = list(col_map.values())
    all_vars = list(var_map.values())

    # 1) Collection organization
    col_score = min(100, len(collections) * 25) if collections else 0
    subchecks.append(audit_subcheck(
        "Collection organization", col_score,
        f"{len(collections)} collections found. Well-structured systems have 3-5 collections (primitive, semantic, component).",
        "pass" if len(collections) >= 3 else ("warn" if collections else "fail"),
        [c.get("name", "") for c in collections[:5]],
        "Variabel Figma dikelompokkan dalam “collection”. Sistem rapi memisahkan token primitif, semantik, dan kadang khusus komponen agar mudah dirawat.",
        [
            "Buat minimal 3 kelompok logis: misalnya Primitives, Semantic (warna/teks/spasi), Components khusus.",
            "Hindari satu collection raksasa untuk semua token; pecah per domain.",
            "Samakan nama collection dengan dokumentasi design token di tim engineering.",
        ],
    ))

    # 2) Mode coverage
    total_modes = sum(len(c.get("modes", [])) for c in collections)
    multi_mode = [c for c in collections if len(c.get("modes", [])) > 1]
    mode_score = min(100, 50 + len(multi_mode) * 25) if collections else 0
    subchecks.append(audit_subcheck(
        "Mode coverage", mode_score,
        f"{total_modes} modes across {len(collections)} collections. {len(multi_mode)} collections have multiple modes (e.g., light/dark).",
        "pass" if multi_mode else ("warn" if collections else "fail"),
        [f"{c.get('name', '')} ({len(c.get('modes', []))} modes)" for c in collections[:5]],
        "Mode (misalnya Light / Dark) memungkinkan nilai token berbeda tanpa duplikasi variabel. Idealnya collection semantik punya mode ganda.",
        [
            "Di Variables, tambahkan mode kedua (Dark) pada collection semantic.",
            "Pastikan token yang perlu berbeda per tema punya nilai di tiap mode.",
            "Uji dengan switch theme prototipe atau plugin untuk memastikan tidak ada yang terlewat.",
        ],
    ))

    # 3) Alias coverage
    alias_count = sum(1 for v in all_vars if isinstance((v.get("valuesByMode") or {}).get(list((v.get("valuesByMode") or {}).keys())[0]) if (v.get("valuesByMode") or {}) else None, dict) and ((v.get("valuesByMode") or {}).get(list((v.get("valuesByMode") or {}).keys())[0]) or {}).get("type") == "VARIABLE_ALIAS")
    alias_pct = alias_count / max(len(all_vars), 1)
    alias_score = min(100, int(alias_pct * 150))
    subchecks.append(audit_subcheck(
        "Alias usage", alias_score,
        f"{alias_count} of {len(all_vars)} variables are aliases. Good systems alias 40-70% of tokens.",
        "pass" if alias_pct > 0.3 else ("warn" if alias_count > 0 else "info"),
        [],
        "Alias berarti variabel A memakai variabel B sebagai nilainya. Ini memudahkan menyatukan “brand blue” ke satu sumber kebenaran.",
        [
            "Ubah token semantic (mis. `color/surface/page`) menjadi alias ke token primitif, bukan hex langsung.",
            "Tingkatkan proporsi alias pada warna dan spacing agar refactor global lebih aman.",
        ],
    ))

    # 4) Token type coverage
    types = set(v.get("resolvedType") for v in all_vars)
    type_score = min(100, len(types) * 30)
    subchecks.append(audit_subcheck(
        "Type diversity", type_score,
        f"Token types used: {', '.join(sorted(types)) if types else 'none'}. Complete systems include COLOR, FLOAT, and STRING.",
        "pass" if len(types) >= 3 else ("warn" if types else "fail"),
        [f"{t}: {sum(1 for v in all_vars if v.get('resolvedType') == t)}" for t in sorted(types)],
        "Figma mendukung variabel COLOR, FLOAT (angka), STRING, BOOLEAN. Sistem lengkap memakai kombinasi untuk warna, radius, spacing, dan teks.",
        [
            "Tambahkan FLOAT untuk spacing, radius, dan ukuran ikon yang konsisten.",
            "Tambahkan STRING untuk font family atau label yang harus konsisten lintas file.",
            "Pastikan tim mendokumentasikan makna tiap tipe untuk desainer baru.",
        ],
    ))

    # 5) Fill binding coverage
    fillable = [n for n in flat_nodes if n["fills"] and n["type"] not in ("DOCUMENT", "CANVAS", "PAGE")]
    bound = sum(1 for n in fillable if n["bound_variables"].get("fills") or n["fill_style_id"])
    bind_pct = bound / max(len(fillable), 1)
    bind_score = max(0, min(100, int(bind_pct * 100)))
    unbound = [n for n in fillable if not n["bound_variables"].get("fills") and not n["fill_style_id"]]
    subchecks.append(audit_subcheck(
        "Fill binding coverage", bind_score,
        f"{bound} of {len(fillable)} nodes have fills bound to variables or styles.",
        "pass" if bind_pct > 0.7 else ("warn" if bind_pct > 0.3 else "fail"),
        [f"{n['name']} ({n['type']}) · id:{n['id']} · {n.get('frame_path','')}" for n in unbound[:5]],
        "Hanya node di dalam scope Folder: yang dihitung. Fill yang terikat variabel/style memastikan tema dan update token otomatis ke layer.",
        [
            "Pilih layer → Fill → klik ikon variabel dan pilih token semantic yang sesuai.",
            "Tidak ada variabel? Buat dulu di collection, lalu apply ulang ke komponen utama.",
            "Prioritaskan komponen publish; instance akan mengikuti master yang sudah ter-token.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


def score_components(flat_nodes, file_meta, scoped_ids=None):
    subchecks = []
    _scoped_ids = scoped_ids or {n["id"] for n in flat_nodes if n.get("id")}
    comp_meta = filter_meta_by_scoped_ids(file_meta.get("components") or {}, _scoped_ids)
    comp_set_meta = filter_meta_by_scoped_ids(file_meta.get("componentSets") or {}, _scoped_ids)
    comp_nodes = [n for n in flat_nodes if n["type"] in ("COMPONENT", "COMPONENT_SET")]
    total_comp = len(comp_meta)

    # 1) Description coverage
    with_desc = {k: v for k, v in comp_meta.items() if (v.get("description") or "").strip()}
    without_desc = {k: v for k, v in comp_meta.items() if not (v.get("description") or "").strip()}
    desc_pct = len(with_desc) / max(total_comp, 1)
    desc_score = max(0, min(100, int(desc_pct * 100)))
    subchecks.append(audit_subcheck(
        "Description coverage", desc_score,
        f"{len(with_desc)} of {total_comp} components have descriptions.",
        "pass" if desc_pct > 0.7 else ("warn" if desc_pct > 0.3 else "fail"),
        [f"{v.get('name', '')} (no description) · id:{k}" for k, v in list(without_desc.items())[:5]],
        "Deskripsi komponen di Figma membantu desainer lain dan developer memahami kapan dan bagaimana memakai komponen tersebut.",
        [
            "Pilih komponen utama → panel kanan → isi Description dengan usage, a11y, dan batasan.",
            "Cantumkan link ke dokumentasi atau Storybook jika ada.",
        ],
    ))

    # 2) Property definitions
    with_props = [n for n in comp_nodes if n["component_properties"]]
    props_pct = len(with_props) / max(len(comp_nodes), 1) if comp_nodes else 0
    props_score = max(0, min(100, int(props_pct * 100)))
    without_props = [n for n in comp_nodes if not n["component_properties"]]
    subchecks.append(audit_subcheck(
        "Property definitions", props_score,
        f"{len(with_props)} of {len(comp_nodes)} component nodes define properties.",
        "pass" if props_pct > 0.5 else ("warn" if with_props else "info"),
        [f"{n['name']} (no properties) · id:{n['id']}" for n in without_props[:5]],
        "Component properties (boolean, instance swap, text, variant) membuat komponen fleksibel tanpa menduplikasi file.",
        [
            "Identifikasi bagian yang sering berubah → jadikan Boolean, Swap instance, atau Text property.",
            "Gunakan variant set untuk kombinasi visibilitas yang kompleks.",
        ],
    ))

    # 3) Variant structure
    sets_count = len(comp_set_meta)
    set_score = min(100, int((sets_count / max(total_comp * 0.05, 1)) * 50)) if total_comp else 100
    subchecks.append(audit_subcheck(
        "Variant structure", set_score,
        f"{sets_count} component sets organize {total_comp} components into variant groups.",
        "pass" if sets_count > 0 else ("warn" if total_comp > 0 else "info"),
        [v.get("name", "") for v in list(comp_set_meta.values())[:5]],
        "Component Set mengelompokkan varian satu komponen (ukuran, state) agar API variant di Figma tetap rapi.",
        [
            "Gabungkan varian terkait ke satu Component Set alih-alih banyak komponen terpisah.",
            "Definisikan properti variant (mis. Size, State) dengan nilai yang jelas.",
        ],
    ))

    # 4) Component count health
    count_score = 100 if total_comp > 0 else 0
    subchecks.append(audit_subcheck(
        "Component inventory", count_score,
        f"{total_comp} components and {sets_count} component sets in the file.",
        "pass" if total_comp > 10 else ("warn" if total_comp > 0 else "fail"),
        [],
        "Indikator seberapa banyak komponen yang terdeteksi di dalam scope Folder: (bukan seluruh file).",
        [
            "Pastikan komponen inti berada di frame `Folder: [Nama Komponen]` agar masuk audit.",
            "Rencanakan refactor jika ada duplikasi atau komponen yang tidak terpakai.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


def score_accessibility(flat_nodes):
    subchecks = []
    text_nodes = [n for n in flat_nodes if n["type"] == "TEXT" and n["font_size"] > 0]

    # 1) Text sizing
    small = [n for n in text_nodes if n["font_size"] < 12]
    size_score = max(0, int(100 * (1 - len(small) / max(len(text_nodes), 1)))) if text_nodes else 100
    subchecks.append(audit_subcheck(
        "Text sizing", size_score,
        f"{len(small)} of {len(text_nodes)} text nodes are below 12px minimum." if text_nodes else "No text nodes to evaluate.",
        "warn" if small else ("info" if not text_nodes else "pass"),
        [f"{n['name']} ({n['font_size']}px) · id:{n['id']} · {n.get('frame_path','')}" for n in small[:5]],
        "Teks di bawah ~12px sulit dibaca banyak pengguna; praktik umum desain dan a11y memakai ukuran minimum yang lebih besar untuk body.",
        [
            "Naikkan ukuran ke skala tipografi terkecil yang sudah disepakati (mis. 12px/14px).",
            "Gunakan text style dari library agar ukuran konsisten.",
        ],
    ))

    # 2) Line height
    lh_bad = [n for n in text_nodes if n["line_height_px"] and n["font_size"] and n["line_height_px"] < n["font_size"] * 1.5]
    lh_score = max(0, int(100 * (1 - len(lh_bad) / max(len(text_nodes), 1)))) if text_nodes else 100
    subchecks.append(audit_subcheck(
        "Line height (WCAG)", lh_score,
        f"{len(lh_bad)} of {len(text_nodes)} text nodes have line-height below 1.5x font size." if text_nodes else "No text nodes to evaluate.",
        "warn" if lh_bad else ("info" if not text_nodes else "pass"),
        [f"{n['name']} ({n['font_size']}px, lh: {n['line_height_px']}px) · id:{n['id']} · {n.get('frame_path','')}" for n in lh_bad[:5]],
        "Line height minimal ~1.5× ukuran font membantu keterbacaan paragraf dan memenuhi pedoman a11y untuk spacing baris.",
        [
            "Atur line height di text style ke auto atau nilai ≥ 1.5× font size.",
            "Periksa ulang paragraf panjang dan label multi-baris.",
        ],
    ))

    # 3) Touch targets
    interactive = [n for n in flat_nodes if n["type"] in ("INSTANCE", "COMPONENT") and (n["width"] > 0 and n["height"] > 0)]
    small_targets = [n for n in interactive if n["width"] < 44 or n["height"] < 44]
    touch_score = max(0, int(100 * (1 - len(small_targets) / max(len(interactive), 1)))) if interactive else 100
    subchecks.append(audit_subcheck(
        "Touch targets", touch_score,
        f"{len(small_targets)} of {len(interactive)} interactive elements are below 44x44px minimum." if interactive else "No interactive elements to evaluate.",
        "warn" if small_targets else ("info" if not interactive else "pass"),
        [f"{n['name']} ({int(n['width'])}x{int(n['height'])}px) · id:{n['id']} · {n.get('frame_path','')}" for n in small_targets[:5]],
        "Area sentuh ~44×44pt (iOS) / minimal sekitar itu (Material) mengurangi kesalahan ketuk; ikon kecil perlu padding hit area.",
        [
            "Perbesar frame klikable atau tambahkan padding invisible di sekitar ikon.",
            "Samakan dengan pola button/icon button yang sudah ada di design system.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


def score_consistency(flat_nodes, file_meta, scoped_ids=None):
    subchecks = []
    _scoped_ids = scoped_ids or {n["id"] for n in flat_nodes if n.get("id")}
    comp_meta = filter_meta_by_scoped_ids(file_meta.get("components") or {}, _scoped_ids)

    # 1) Duplicate component names
    names = [v.get("name", "") for v in comp_meta.values()]
    name_counts = Counter(names)
    dupes = {n: c for n, c in name_counts.items() if c > 1}
    dupe_score = max(0, 100 - len(dupes) * 10)
    subchecks.append(audit_subcheck(
        "Duplicate components", dupe_score,
        f"{len(dupes)} component names are duplicated." if dupes else "No duplicate component names found.",
        "warn" if dupes else "pass",
        [f"{n} (×{c})" for n, c in list(dupes.items())[:5]],
        "Beberapa komponen berbeda dengan nama sama membingungkan saat search, publish library, dan integrasi kode.",
        [
            "Rename agar unik atau gabungkan jika memang duplikat tidak sengaja.",
            "Gunakan prefix halaman/kategori jika nama konflik tidak bisa dihindari.",
        ],
    ))

    # 2) Hardcoded fills
    hardcoded = [n for n in flat_nodes if n["fills"] and not n["bound_variables"].get("fills") and not n["fill_style_id"] and n["type"] not in ("DOCUMENT", "CANVAS", "PAGE")]
    hc_score = max(0, min(100, 100 - min(len(hardcoded), 50) * 2))
    subchecks.append(audit_subcheck(
        "Hardcoded values", hc_score,
        f"{len(hardcoded)} nodes use hardcoded fill colors not bound to variables or styles.",
        "warn" if hardcoded else "pass",
        [f"{n['name']} ({n['type']}) · id:{n['id']} · {n.get('frame_path','')}" for n in hardcoded[:5]],
        "Fill mentah (hex tanpa variabel) tidak ikut berubah ketika tema atau token di-update.",
        [
            "Ganti fill dengan variabel semantic atau style library.",
            "Periksa nested layer di dalam komponen; sering warna “tersembunyi” di sub-layer.",
        ],
    ))

    # 3) Default layer names
    all_default = [n for n in flat_nodes if DEFAULT_PATTERN.match(n["name"])]
    def_score = max(0, int(100 * (1 - len(all_default) / max(len(flat_nodes), 1))))
    subchecks.append(audit_subcheck(
        "Layer naming quality", def_score,
        f"{len(all_default)} of {len(flat_nodes)} layers use default names (Vector, Group, Frame, etc.).",
        "warn" if all_default else "pass",
        [f"{n['name']} ({n['type']}) · id:{n['id']} · {n.get('frame_path','')}" for n in all_default[:5]],
        "Nama layer default menyulitkan debugging, kolaborasi, dan plugin yang membaca struktur layer.",
        [
            "Rename layer sesuai fungsi: `Icon`, `Label`, `Background`, `Border`.",
            "Rapikan hierarchy: grup yang jelas sebelum handoff ke dev.",
        ],
    ))

    # 4) Instance usage
    instances = [n for n in flat_nodes if n["type"] == "INSTANCE"]
    total_non_util = [n for n in flat_nodes if n["type"] not in ("DOCUMENT", "CANVAS", "PAGE")]
    inst_pct = len(instances) / max(len(total_non_util), 1)
    inst_score = min(100, int(inst_pct * 200))
    subchecks.append(audit_subcheck(
        "Component reuse", inst_score,
        f"{len(instances)} instances used across {len(total_non_util)} nodes ({int(inst_pct * 100)}% reuse rate).",
        "pass" if inst_pct > 0.3 else ("warn" if instances else "info"),
        [],
        "Proporsi instance vs layer biasa di scope Folder: mengindikasikan apakah tim memakai komponen library, bukan menduplikasi frame.",
        [
            "Ganti salinan static dengan Instance dari komponen master.",
            "Publikasikan atau perbarui library agar instance mudah diakses tim.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


def score_coverage(flat_nodes, file_meta, scoped_ids=None):
    subchecks = []
    _scoped_ids = scoped_ids or {n["id"] for n in flat_nodes if n.get("id")}

    # 1) Text style coverage
    text_nodes = [n for n in flat_nodes if n["type"] == "TEXT"]
    styled_text = [n for n in text_nodes if n["text_style_id"]]
    unstyled_text = [n for n in text_nodes if not n["text_style_id"]]
    text_pct = len(styled_text) / max(len(text_nodes), 1) if text_nodes else 1
    text_score = max(0, min(100, int(text_pct * 100)))
    subchecks.append(audit_subcheck(
        "Text style coverage", text_score,
        f"{len(styled_text)} of {len(text_nodes)} text nodes use a text style." if text_nodes else "No text nodes found.",
        "pass" if text_pct > 0.8 else ("warn" if text_pct > 0.4 else "fail"),
        [f"{n['name']} (no text style) · id:{n['id']} · {n.get('frame_path','')}" for n in unstyled_text[:5]],
        "Text style memastikan tipografi konsisten dan mudah diubah global (font, weight, size) selaras dengan token.",
        [
            "Buat atau pakai text style dari library untuk semua teks UI.",
            "Hapus override manual kecuali untuk kasus khusus yang didokumentasikan.",
        ],
    ))

    # 2) Fill style/variable coverage
    fillable = [n for n in flat_nodes if n["fills"] and n["type"] not in ("DOCUMENT", "CANVAS", "PAGE")]
    fill_covered = [n for n in fillable if n["fill_style_id"] or n["bound_variables"].get("fills")]
    fill_uncovered = [n for n in fillable if not n["fill_style_id"] and not n["bound_variables"].get("fills")]
    fill_pct = len(fill_covered) / max(len(fillable), 1) if fillable else 1
    fill_score = max(0, min(100, int(fill_pct * 100)))
    subchecks.append(audit_subcheck(
        "Fill coverage", fill_score,
        f"{len(fill_covered)} of {len(fillable)} nodes have fills covered by styles or variables." if fillable else "No fillable nodes found.",
        "pass" if fill_pct > 0.7 else ("warn" if fill_pct > 0.3 else "fail"),
        [f"{n['name']} ({n['type']}) · id:{n['id']} · {n.get('frame_path','')}" for n in fill_uncovered[:5]],
        "Layer dengan fill sebaiknya memakai paint style atau variabel agar tema dan brand konsisten.",
        [
            "Terapkan color style atau variabel ke fill yang masih ‘custom’.",
            "Sinkronkan nama style dengan token engineering bila memungkinkan.",
        ],
    ))

    # 3) Effect style coverage
    effect_nodes = [n for n in flat_nodes if n["effect_style_id"]]
    eff_score = 100 if effect_nodes else 50
    subchecks.append(audit_subcheck(
        "Effect style usage", eff_score,
        f"{len(effect_nodes)} nodes use effect styles." if effect_nodes else "No effect styles found in use.",
        "pass" if effect_nodes else "info",
        [f"{n['name']}" for n in effect_nodes[:5]],
        "Effect style (shadow, blur) yang terpusat memudahkan menyamakan elevasi dan konsistensi visual.",
        [
            "Buat effect style untuk drop shadow standar (elevation 1–4) lalu apply ke kartu, modal, tombol.",
            "Jika belum perlu shadow di scope ini, abaikan skor info atau kecilkan penggunaan efek manual.",
        ],
    ))

    # 4) Component presence
    comp_meta = filter_meta_by_scoped_ids(file_meta.get("components") or {}, _scoped_ids)
    comp_score = 100 if len(comp_meta) > 0 else 0
    subchecks.append(audit_subcheck(
        "Core component presence", comp_score,
        f"{len(comp_meta)} components found in the design system.",
        "pass" if comp_meta else "fail",
        [v.get("name", "") for v in list(comp_meta.values())[:5]],
        "Memastikan setidaknya ada komponen master di dalam scope Folder: yang Anda audit.",
        [
            "Pastikan master component sudah dibuat dan berada di dalam frame `Folder: [Nama]`.",
            "Token Variables API gagal tidak mempengaruhi hitungan ini; ini murni dari struktur file.",
        ],
    ))

    overall = int(sum(s["score"] for s in subchecks) / max(len(subchecks), 1))
    return overall, subchecks


# ─── Full audit pipeline ─────────────────────────────────────────────

def run_full_audit(figma_url: str, token: str):
    parsed = parse_figma_url(figma_url)
    if not parsed["file_key"]:
        raise ValueError("URL Figma tidak valid")

    file_data = fetch_file(parsed["file_key"], token, node_id=None, depth=10)
    variables_data = fetch_variables(parsed["file_key"], token)

    doc = file_data.get("document") or {}
    file_name = file_data.get("name") or "Untitled"

    flat = walk_tree(doc)
    scoped_flat = filter_nodes_folder_only(flat)
    scoped_ids = {n["id"] for n in scoped_flat if n.get("id")}

    folder_frames_found = set()
    for n in scoped_flat:
        for seg in (n.get("frame_path") or "").split("/"):
            seg = seg.strip()
            if is_folder_component_frame_name(seg):
                folder_frames_found.add(seg)
    print(f"[Audit] File: {file_name}")
    print(f"[Audit] Total nodes: {len(flat)}, Scoped nodes (inside Folder: frames): {len(scoped_flat)}, Scoped IDs: {len(scoped_ids)}")
    print(f"[Audit] Folder: frames detected ({len(folder_frames_found)}): {sorted(folder_frames_found)}")

    s_naming, c_naming = score_naming(scoped_flat, variables_data)
    s_tokens, c_tokens = score_tokens(scoped_flat, variables_data)
    s_components, c_components = score_components(scoped_flat, file_data, scoped_ids)
    s_access, c_access = score_accessibility(scoped_flat)
    s_consist, c_consist = score_consistency(scoped_flat, file_data, scoped_ids)
    s_coverage, c_coverage = score_coverage(scoped_flat, file_data, scoped_ids)

    total = int((s_naming + s_tokens + s_components + s_access + s_consist + s_coverage) / 6)

    var_meta_root = variables_data.get("meta") or {}
    var_collections = var_meta_root.get("variableCollections") or {}
    var_count = sum(len(c.get("variableIds", [])) for c in var_collections.values())
    col_count = len(var_collections)

    comp_id_to_tree_path = {}
    for n in scoped_flat:
        if n.get("type") in ("COMPONENT", "COMPONENT_SET") and n.get("id"):
            comp_id_to_tree_path[n["id"]] = n.get("frame_path") or ""

    comp_meta = filter_meta_by_scoped_ids(file_data.get("components") or {}, scoped_ids)
    categories = {}
    for comp_id, comp in comp_meta.items():
        containing = comp.get("containingFrame") or {}
        page = containing.get("pageName", "Unknown") if isinstance(containing, dict) else "Unknown"
        raw_frame = containing.get("name") if isinstance(containing, dict) else None
        frame_name = (raw_frame or "").strip() or "Uncategorized"
        key = frame_name
        if key not in categories:
            categories[key] = {"name": key, "page": page, "components": [], "count": 0}
        tree_path = comp_id_to_tree_path.get(comp_id, "")
        categories[key]["components"].append({
            "id": comp_id,
            "name": comp.get("name", ""),
            "description": comp.get("description", ""),
            "frame": frame_name,
            "tree_path": tree_path,
        })
        categories[key]["count"] += 1

    for _cat in categories.values():
        names = [c.get("name") for c in _cat["components"] if c.get("name")]
        _cat["component_names"] = sorted(set(names), key=lambda x: (x or "").lower())

    issues = []
    for cat_data in [c_naming, c_tokens, c_components, c_access, c_consist, c_coverage]:
        for check in cat_data:
            if check["icon"] in ("warn", "fail") and check["score"] < 80:
                issues.append(check)
    issues.sort(key=lambda x: x["score"])

    status = "excellent" if total >= 90 else "good" if total >= 75 else "needs-work" if total >= 60 else "critical"

    return {
        "file_name": file_name,
        "file_key": parsed["file_key"],
        "figma_url": figma_url,
        "timestamp": datetime.now().isoformat(),
        "total_score": total,
        "status": status,
        "variables_count": var_count,
        "collections_count": col_count,
        "total_nodes": len(flat),
        "scoped_nodes": len(scoped_flat),
        "folder_frames": sorted(folder_frames_found),
        "categories_scores": {
            "naming": {"score": s_naming, "checks": c_naming},
            "tokens": {"score": s_tokens, "checks": c_tokens},
            "components": {"score": s_components, "checks": c_components},
            "accessibility": {"score": s_access, "checks": c_access},
            "consistency": {"score": s_consist, "checks": c_consist},
            "coverage": {"score": s_coverage, "checks": c_coverage},
        },
        "component_categories": sorted(categories.values(), key=lambda x: -x["count"]),
        "top_issues": issues[:10],
    }


# ─── Export documentation ─────────────────────────────────────────────

def detect_viewport(comp_name: str, frame_name: str, width: float = 0) -> str:
    lower = (comp_name + " " + frame_name).lower()
    if any(kw in lower for kw in ("mobile", "phone", "sm", "responsive", "android", "ios")):
        return "mobile"
    if any(kw in lower for kw in ("desktop", "web", "lg", "xl", "screen")):
        return "desktop"
    if width and width < 768:
        return "mobile"
    return "desktop"


def generate_doc(comp, audit_result, viewport):
    cat_scores = audit_result["categories_scores"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Audit: {comp['name']} - {viewport.capitalize()}", "",
        f"**File Figma:** {audit_result['file_name']}",
        f"**Frame:** {comp.get('frame', 'N/A')}",
        f"**Tanggal audit:** {now}",
        f"**Component ID:** {comp.get('id', 'N/A')}", "",
        "## Skor Ringkas", "", "| Kategori | Skor |", "|---|---|",
    ]
    for key, label in [("naming", "Naming"), ("tokens", "Tokens"), ("components", "Components"),
                       ("accessibility", "Accessibility"), ("consistency", "Consistency"), ("coverage", "Coverage")]:
        lines.append(f"| {label} | {cat_scores[key]['score']}/100 |")
    lines.append(f"| **Total** | **{audit_result['total_score']}/100** |")
    lines.append("")
    lines.append("## Temuan Detail")
    lines.append("")
    for key in ("naming", "tokens", "components", "accessibility", "consistency", "coverage"):
        for ch in cat_scores[key]["checks"]:
            icon = "🔴" if ch["icon"] == "fail" else "🟡" if ch["icon"] == "warn" else "🟢" if ch["icon"] == "pass" else "ℹ️"
            lines.append(f"### {icon} {ch['label']} ({ch['score']}/100)")
            lines.append(f"{ch['description']}")
            if ch.get("explanation"):
                lines.append("")
                lines.append(f"**Penjelasan:** {ch['explanation']}")
            fixes = ch.get("how_to_fix") or []
            if fixes:
                lines.append("")
                lines.append("**Cara memperbaiki:**")
                for step in fixes:
                    lines.append(f"- {step}")
            if ch.get("examples"):
                lines.append("")
                lines.append("**Contoh temuan:**")
                for ex in ch["examples"]:
                    lines.append(f"  - `{ex}`")
            lines.append("")
    lines.append("## Risiko Jika Ditunda")
    if audit_result["total_score"] < 60:
        lines.append("- Design system kritis, risiko inkonsistensi tinggi.")
    elif audit_result["total_score"] < 75:
        lines.append("- Beberapa area perlu perbaikan untuk kualitas handoff.")
    else:
        lines.append("- Risiko rendah, pertahankan kualitas.")
    lines.append("")
    return "\n".join(lines)


def export_documentation(audit_result, base_path=None):
    base = Path(base_path or WORKSPACE)
    exported = []
    for cat in audit_result.get("component_categories", []):
        frame_name = cat["name"]
        for comp in cat.get("components", []):
            viewport = detect_viewport(comp["name"], frame_name)
            safe_frame = re.sub(r'[<>:"/\\|?*]', '_', frame_name)
            safe_comp = re.sub(r'[<>"/\\|?*]', '_', comp["name"])
            folder = base / f"{safe_frame}:{safe_comp}"
            folder.mkdir(parents=True, exist_ok=True)
            content = generate_doc(comp, audit_result, viewport)
            fp = folder / f"{viewport}.md"
            fp.write_text(content, encoding="utf-8")
            exported.append({"folder": f"{safe_frame}:{safe_comp}", "file": f"{viewport}.md", "path": str(fp)})
    return exported


# ─── Flask routes ─────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/audit", methods=["POST"])
def api_audit():
    data = request.json or {}
    figma_url = data.get("figmaUrl", "")
    token = data.get("token", "")
    if not figma_url or not token:
        return jsonify({"error": "Figma URL dan Personal Access Token wajib diisi"}), 400
    try:
        result = run_full_audit(figma_url, token)
        return jsonify(result)
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response is not None else 500
        if status == 403:
            return jsonify({"error": "Token tidak valid atau tidak punya akses ke file ini"}), 403
        if status == 404:
            return jsonify({"error": "File Figma tidak ditemukan"}), 404
        return jsonify({"error": f"Figma API error: {status}"}), status
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"}), 500


@app.route("/api/tokens", methods=["POST"])
def api_tokens():
    data = request.json or {}
    figma_url = data.get("figmaUrl", "")
    token = data.get("token", "")
    if not figma_url or not token:
        return jsonify({"error": "Figma URL dan token wajib diisi"}), 400
    try:
        parsed = parse_figma_url(figma_url)
        if not parsed["file_key"]:
            raise ValueError("URL tidak valid")
        file_data = fetch_file(parsed["file_key"], token, depth=1)
        variables_data = fetch_variables(parsed["file_key"], token, strict=True)
        tokens = organize_tokens(variables_data)
        tokens["file_name"] = file_data.get("name") or "Untitled"
        return jsonify(tokens)
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def api_export():
    data = request.json or {}
    results = data.get("results")
    if not results:
        return jsonify({"error": "Tidak ada data audit untuk di-export"}), 400
    try:
        exported = export_documentation(results, str(WORKSPACE))
        return jsonify({"success": True, "exported": exported, "count": len(exported), "base_path": str(WORKSPACE)})
    except Exception as e:
        return jsonify({"error": f"Export gagal: {str(e)}"}), 500


@app.route("/api/token-diagnostics", methods=["POST"])
def api_token_diagnostics():
    data = request.json or {}
    figma_url = data.get("figmaUrl", "")
    token = data.get("token", "")
    if not figma_url or not token:
        return jsonify({"error": "Figma URL dan token wajib diisi"}), 400
    parsed = parse_figma_url(figma_url)
    if not parsed["file_key"]:
        return jsonify({"error": "URL tidak valid"}), 400

    headers = {"X-Figma-Token": token}
    checks = []

    for label, endpoint in [
        ("me", f"{FIGMA_API}/me"),
        ("file", f"{FIGMA_API}/files/{parsed['file_key']}"),
        ("variables", f"{FIGMA_API}/files/{parsed['file_key']}/variables/local"),
    ]:
        try:
            r = requests.get(endpoint, headers=headers, timeout=30)
            checks.append({
                "check": label,
                "status_code": r.status_code,
                "ok": r.status_code < 400,
                "message": None if r.status_code < 400 else (r.text[:220] if r.text else "error"),
            })
        except Exception as e:
            checks.append({"check": label, "status_code": 0, "ok": False, "message": str(e)})

    return jsonify({"file_key": parsed["file_key"], "checks": checks})


if __name__ == "__main__":
    app.run(debug=True, port=5555)
