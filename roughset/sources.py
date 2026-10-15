from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import json, re, urllib.request

SUPPORTED_LOCAL_EXTENSIONS={'.csv','.xlsx','.xls'}
KNOWN_UCI_DOI_TO_ID={
    '10.24432/c5501t':44,
    '10.24432/c5jp48':19,
    '10.24432/c5488x':12,
}

@dataclass(frozen=True)
class UCISource:
    kind: str
    value: str


def discover_local_files(folder: Path) -> List[Path]:
    folder=Path(folder)
    if not folder.exists(): return []
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_LOCAL_EXTENSIONS], key=lambda p:p.name.lower())


def parse_uci_sources(path: Path) -> List[UCISource]:
    path=Path(path)
    if not path.exists(): return []
    items=[]
    for line_no, raw in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        line=raw.strip()
        if not line or line.startswith('#'): continue
        if ':' in line and line.split(':', 1)[0].strip().lower() in {'uci_id', 'doi'}:
            kind, value = line.split(':', 1)
            kind = kind.strip().lower(); value = value.strip()
        elif line.isdigit():
            kind, value = 'uci_id', line
        elif line.lower().startswith('https://doi.org/'):
            kind, value = 'doi', line[len('https://doi.org/'):].strip()
        elif line.lower().startswith('http://doi.org/'):
            kind, value = 'doi', line[len('http://doi.org/'):].strip()
        elif line.lower().startswith('10.') and '/' in line:
            kind, value = 'doi', line
        else:
            raise ValueError(f"Invalid UCI source at line {line_no}: {raw}")
        if not value: raise ValueError(f"Invalid UCI source at line {line_no}: {raw}")
        if kind=='uci_id' and not value.isdigit(): raise ValueError(f"UCI ID must be numeric at line {line_no}.")
        items.append(UCISource(kind,value))
    return items


def resolve_uci_doi(doi: str, cache_file: Optional[Path]=None, timeout: int=15) -> int:
    doi=doi.strip()
    doi_key=doi.lower()
    cache={}
    if cache_file:
        cache_file=Path(cache_file)
        if cache_file.exists():
            try: cache=json.loads(cache_file.read_text(encoding='utf-8'))
            except Exception: cache={}
    normalized_cache={str(k).lower(): v for k,v in cache.items()}
    if doi_key in normalized_cache: return int(normalized_cache[doi_key])
    if doi_key in KNOWN_UCI_DOI_TO_ID: uci_id=KNOWN_UCI_DOI_TO_ID[doi_key]
    else:
        try:
            req=urllib.request.Request(f"https://doi.org/{doi}",headers={'User-Agent':'RoughSetResearchSoftware/1.0'})
            with urllib.request.urlopen(req,timeout=timeout) as resp:
                final_url=resp.geturl()
            m=re.search(r'/dataset/(\d+)(?:/|$)',final_url)
            if not m: raise ValueError(f"DOI resolved to '{final_url}', but no UCI dataset ID was found.")
            uci_id=int(m.group(1))
        except Exception as exc:
            raise RuntimeError(f"Could not resolve UCI DOI '{doi}'. Use 'uci_id:<number>' when offline. Detail: {exc}") from exc
    if cache_file:
        cache[str(doi)]=int(uci_id); cache_file.parent.mkdir(parents=True,exist_ok=True); cache_file.write_text(json.dumps(cache,ensure_ascii=False,indent=2),encoding='utf-8')
    return int(uci_id)
