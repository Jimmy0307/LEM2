from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import zipfile
import zlib
from pathlib import Path

from lxml import etree

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
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
                        by_id = {sid: child for child in sp_tree if (sid := child_shape_id(child)) is not None}
                        shape_map = patch["shapes"]
                        assert isinstance(shape_map, dict)
                        for shape_id, shape_xml in shape_map.items():
                            old = by_id.get(int(shape_id))
                            if old is None:
                                raise RuntimeError(
                                    f"slide {slide_no}: missing shape id {shape_id}; available={sorted(by_id)}"
                                )
                            new = etree.fromstring(str(shape_xml).encode("utf-8"))
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
