from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import zipfile
import zlib
from difflib import SequenceMatcher
from pathlib import Path

from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PAYLOAD_SHA256 = "d99d072479df81a120a2af88cf745ddb1fb4aed7c3f6ffba6aec89799dc79fdb"


def load_payload(parts_dir: Path) -> dict[str, str]:
    parts = sorted(parts_dir.glob("part_*.b64"))
    if not parts:
        raise FileNotFoundError(f"no audit payload parts found in {parts_dir}")
    encoded = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    digest = hashlib.sha256(encoded.encode("ascii")).hexdigest()
    if digest != PAYLOAD_SHA256:
        raise RuntimeError(f"audit payload SHA mismatch: {digest}")
    return json.loads(zlib.decompress(base64.b64decode(encoded)).decode("utf-8"))


def group_payload(payload: dict[str, str]) -> dict[int, dict[str, object]]:
    grouped: dict[int, dict[str, object]] = {}
    for key, value in payload.items():
        if key.startswith("slide:"):
            slide_no = int(key.split(":", 1)[1])
            grouped.setdefault(slide_no, {"whole": None, "shapes": {}})["whole"] = value
        elif key.startswith("shape:"):
            _, slide_s, shape_id_s = key.split(":")
            shape_map = grouped.setdefault(int(slide_s), {"whole": None, "shapes": {}})["shapes"]
            assert isinstance(shape_map, dict)
            shape_map[int(shape_id_s)] = value
        else:
            raise RuntimeError(f"unsupported audit payload key: {key}")
    return grouped


def child_shape_id(element: etree._Element) -> int | None:
    nv = element.find(f".//{{{P_NS}}}cNvPr")
    if nv is None or nv.get("id") is None:
        return None
    return int(nv.get("id"))


def shape_name(element: etree._Element) -> str | None:
    nv = element.find(f".//{{{P_NS}}}cNvPr")
    return nv.get("name") if nv is not None else None


def shape_kind(element: etree._Element) -> str:
    return etree.QName(element).localname


def shape_geometry(element: etree._Element) -> tuple[int, int, int, int] | None:
    xfrm = element.find(f".//{{{A_NS}}}xfrm")
    if xfrm is None:
        xfrm = element.find(f".//{{{P_NS}}}xfrm")
    if xfrm is None:
        return None
    off = None
    ext = None
    for child in xfrm.iterchildren():
        local = etree.QName(child).localname
        if local == "off" and off is None:
            off = child
        elif local == "ext" and ext is None:
            ext = child
    if off is None or ext is None:
        return None
    try:
        return (
            int(off.get("x")),
            int(off.get("y")),
            int(ext.get("cx")),
            int(ext.get("cy")),
        )
    except (TypeError, ValueError):
        return None


def shape_text(element: etree._Element) -> str:
    return "\n".join(t.text or "" for t in element.findall(f".//{{{A_NS}}}t")).strip()


def resolve_shape(
    slide_no: int,
    sp_tree: etree._Element,
    desired_id: int,
    target: etree._Element,
) -> etree._Element:
    children = [child for child in sp_tree if child_shape_id(child) is not None]
    by_id = {child_shape_id(child): child for child in children}

    target_kind = shape_kind(target)
    target_geom = shape_geometry(target)
    target_name = shape_name(target)
    target_text = shape_text(target)
    same_kind = [c for c in children if shape_kind(c) == target_kind]

    if target_geom is not None:
        geom_matches = [c for c in same_kind if shape_geometry(c) == target_geom]
        if len(geom_matches) == 1:
            return geom_matches[0]
        if len(geom_matches) > 1 and target_name:
            named = [c for c in geom_matches if shape_name(c) == target_name]
            if len(named) == 1:
                return named[0]

        tx, ty, tcx, tcy = target_geom
        relaxed = []
        for c in same_kind:
            geom = shape_geometry(c)
            if geom is None:
                continue
            x, y, cx, cy = geom
            if (
                abs(x - tx) <= 25000
                and abs(cx - tcx) <= 100000
                and abs(y - ty) <= 250000
                and abs(abs(cy) - abs(tcy)) <= 75000
            ):
                relaxed.append(c)
        if len(relaxed) == 1:
            return relaxed[0]

    if target_name:
        name_matches = [c for c in same_kind if shape_name(c) == target_name]
        if len(name_matches) == 1:
            return name_matches[0]

    if target_text:
        scored = []
        for c in same_kind:
            source_text = shape_text(c)
            if not source_text:
                continue
            score = SequenceMatcher(None, target_text, source_text).ratio()
            scored.append((score, c))
        scored.sort(key=lambda item: item[0], reverse=True)
        if scored:
            best_score, best = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else 0.0
            if best_score >= 0.62 and (best_score - second_score) >= 0.08:
                return best

    direct = by_id.get(desired_id)
    if direct is not None and shape_kind(direct) == target_kind:
        return direct

    if target_text:
        text_matches = [c for c in same_kind if shape_text(c) == target_text]
        if len(text_matches) == 1:
            return text_matches[0]

    available = [
        {
            "id": child_shape_id(c),
            "kind": shape_kind(c),
            "name": shape_name(c),
            "geom": shape_geometry(c),
            "text": shape_text(c)[:80],
        }
        for c in same_kind
    ]
    raise RuntimeError(
        f"slide {slide_no}: cannot resolve shape id {desired_id}; "
        f"target={{'kind': {target_kind!r}, 'name': {target_name!r}, "
        f"'geom': {target_geom!r}, 'text': {target_text[:80]!r}}}; "
        f"same-kind candidates={available}"
    )


def patch_deck(source: Path, output: Path, payload: dict[str, str]) -> str:
    grouped = group_payload(payload)
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source, "r") as zin, zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            match = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", info.filename)
            if match:
                slide_no = int(match.group(1))
                patch = grouped.get(slide_no)
                if patch:
                    whole = patch["whole"]
                    if isinstance(whole, str):
                        data = whole.encode("utf-8")
                    else:
                        root = etree.fromstring(data)
                        sp_tree = root.find(f".//{{{P_NS}}}spTree")
                        if sp_tree is None:
                            raise RuntimeError(f"slide {slide_no}: missing spTree")
                        shape_map = patch["shapes"]
                        assert isinstance(shape_map, dict)
                        for shape_id, shape_xml in shape_map.items():
                            new = etree.fromstring(str(shape_xml).encode("utf-8"))
                            old = resolve_shape(slide_no, sp_tree, int(shape_id), new)
                            old_nv = old.find(f".//{{{P_NS}}}cNvPr")
                            new_nv = new.find(f".//{{{P_NS}}}cNvPr")
                            if old_nv is not None and new_nv is not None:
                                if old_nv.get("id") is not None:
                                    new_nv.set("id", old_nv.get("id"))
                                if old_nv.get("name") is not None:
                                    new_nv.set("name", old_nv.get("name"))
                            sp_tree.replace(old, new)
                        data = etree.tostring(
                            root,
                            xml_declaration=True,
                            encoding="UTF-8",
                            standalone=True,
                        )
            zout.writestr(info, data)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{digest}  {output.name}\n", encoding="utf-8"
    )
    return digest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--payload-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = load_payload(args.payload_dir)
    digest = patch_deck(args.source, args.output, payload)
    print(
        "CONFLICT_ANATOMY_AUDIT_PATCH=PASS",
        f"entries={len(payload)}",
        f"sha256={digest}",
    )


if __name__ == "__main__":
    main()
