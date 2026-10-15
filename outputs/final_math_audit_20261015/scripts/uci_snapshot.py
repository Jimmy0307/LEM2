"""Freeze the three UCI tables once so pre-fix and post-fix runs read identical bytes.

snapshot: fetch with ucimlrepo and write <dir>/uci_<id>_{features,targets}.csv + .pkl + meta.json
replay_fetcher(dir): a drop-in `fetcher` for roughset.adapters.load_uci_dataset_by_id
"""
from __future__ import annotations
import hashlib, json, pickle, sys
from pathlib import Path
from types import SimpleNamespace

IDS = (44, 19, 12)

def snapshot(folder: Path):
    # The corporate network re-signs TLS; use the Windows trust store for this one-off fetch only.
    import truststore
    truststore.inject_into_ssl()
    from ucimlrepo import fetch_ucirepo
    folder.mkdir(parents=True, exist_ok=True)
    meta = {}
    for uci_id in IDS:
        ds = fetch_ucirepo(id=uci_id)
        X, y = ds.data.features, ds.data.targets
        X.to_csv(folder / f"uci_{uci_id}_features.csv", index=False)
        y.to_csv(folder / f"uci_{uci_id}_targets.csv", index=False)
        with open(folder / f"uci_{uci_id}.pkl", "wb") as fh:
            pickle.dump({"features": X, "targets": y, "name": ds.metadata.name}, fh)
        meta[uci_id] = {"name": ds.metadata.name, "rows": int(len(X)), "features": list(X.columns),
                        "targets": list(y.columns)}
    for p in sorted(folder.glob("uci_*")):
        meta.setdefault("sha256", {})[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (folder / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=1))

def replay_fetcher(folder: Path):
    folder = Path(folder)
    def fetch(id: int):
        with open(folder / f"uci_{int(id)}.pkl", "rb") as fh:
            d = pickle.load(fh)
        return SimpleNamespace(data=SimpleNamespace(features=d["features"].copy(), targets=d["targets"].copy()),
                               metadata=SimpleNamespace(name=d["name"]))
    return fetch

if __name__ == "__main__":
    snapshot(Path(sys.argv[1]))
