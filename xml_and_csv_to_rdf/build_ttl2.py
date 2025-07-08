#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convert every *.csv in the current directory (same column layout as catinella.csv)
into ONE Turtle file: combined.ttl

Usage:
    python build_ttl2.py
"""

from __future__ import annotations
import re
import pandas as pd
from pathlib import Path
from rdflib import Graph, Namespace, URIRef, Literal

# ------------------------------------------------------------------------
# 1. All of the prefixes  (from prefixes.csv)
# ------------------------------------------------------------------------
PREFIXES: dict[str, str] = {
    "val"     : "https://github.com/Vallecupola-Ecosystem/Exhibition/entities/",
    "crm"     : "http://www.cidoc-crm.org/cidoc-crm/",
    "schema"  : "https://schema.org/",
    "dcterms" : "http://purl.org/dc/terms/",
    "dc"      : "http://purl.org/dc/elements/1.1/",
    "pico"    : "http://data.cochrane.org/ontologies/pico/",
    "a-cd"    : "https://w3id.org/arco/ontology/context-description/",
    "a-dd"    : "https://w3id.org/arco/ontology/denotative-description/",
    "frbr"    : "http://purl.org/vocab/frbr/core#",
    "rdf"     : "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs"    : "http://www.w3.org/2000/01/rdf-schema#",
    "foaf"    : "http://xmlns.com/foaf/0.1/",
    "frbroo"  : "http://iflastandards.info/ns/fr/frbr/frbroo/",
    "fabio"   : "http://purl.org/spar/fabio/",
    "mo"      : "http://purl.org/ontology/mo/",
    "event"   : "http://purl.org/NET/c4dm/event.owl#",
    "nmo"     : "http://nomisma.org/ontology#",
    "skos"    : "http://www.w3.org/2004/02/skos/core#",
    "prov"    : "http://www.w3.org/ns/prov#",
    "owl"     : "http://www.w3.org/2002/07/owl#",
    "dbpedia" : "http://dbpedia.org/ontology/",
    "dcmitype": "http://purl.org/dc/dcmitype/",
    "gn"      : "http://sws.geonames.org/",
    "aat"     : "http://vocab.getty.edu/aat/",
    "iso639"  : "http://id.loc.gov/vocabulary/iso639-2/",
    "wd"      : "https://www.wikidata.org/wiki/",
    "xsd"     : "http://www.w3.org/2001/XMLSchema#",
    "qudt"    : "http://qudt.org/schema/qudt/",
}

# ------------------------------------------------------------------------
# 2. The preparation of RE
# ------------------------------------------------------------------------
CURIE_RE       = re.compile(r'^([A-Za-z_][\w\-]*):([\w\-\.]+)$')
URI_ANG_RE     = re.compile(r'^<([^>]+)>$')
URI_INLINE_RE  = re.compile(r'<([^>]+)>\s*|https?://[^\s>]+')

# Literal
LITERAL_LANG_RE = re.compile(r'^"(.+?)"(?:@([a-z\-]+))?$', re.S)
LITERAL_TYPE_RE = re.compile(
    r'^"(.+?)"\^\^(?:<([^>]+)>|([A-Za-z_][\w\-]*:[\w\-\.]+))$',
    re.S,
)

# ------------------------------------------------------------------------
# 3. Utility function
# ------------------------------------------------------------------------
SMART_QUOTES = {
    "“": '"', "”": '"', "«": '"', "»": '"', "„": '"', "‹": '"', "›": '"',
    "‘": "'", "’": "'",
}
def clean_quotes(text: str) -> str:
    """Replace curly quotes with straight quotes to avoid regular expression matching failure"""
    return "".join(SMART_QUOTES.get(ch, ch) for ch in text)

def expand_curie(text: str) -> str | None:
    m = CURIE_RE.fullmatch(text)
    if not m:
        return None
    prefix, local = m.groups()
    base = PREFIXES.get(prefix)
    return f"{base}{local}" if base else None

def to_uri(text: str) -> URIRef | None:
    """String -> URIRef; if not a URI / CURIE, returns None"""
    text = text.strip()
    # surrounded by angle brackets
    m = URI_ANG_RE.fullmatch(text)
    if m:
        return URIRef(m.group(1))
    # full http(s)
    if text.startswith(("http://", "https://")):
        return URIRef(text)
    # CURIE
    full = expand_curie(text)
    return URIRef(full) if full else None

# ------------------------------------------------------------------------
# 4. Dealing with single CSV
# ------------------------------------------------------------------------
REQUIRED_COLS = {"Subject (URI)", "Predicate (URI)", "Object (URI)"}

def csv_to_graph(csv_path: Path, g: Graph) -> None:
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"❌  cannot read {csv_path.name}: {e}")
        return

    if not REQUIRED_COLS.issubset(df.columns):
        print(f"ℹ️  skip {csv_path.name}: missing required columns")
        return

    for _, row in df.iterrows():
        s_raw = str(row["Subject (URI)"]).strip()
        p_raw = str(row["Predicate (URI)"]).strip()
        o_raw = str(row["Object (URI)"]).strip()
        o_raw = clean_quotes(o_raw)

        s = to_uri(s_raw)
        p = to_uri(p_raw)
        if not (s and p):
            print(f"⚠️  [skip] {csv_path.name}: bad S/P -> {s_raw}  {p_raw}")
            continue

        # ---------- 4A Language literals ----------
        m_lang = LITERAL_LANG_RE.fullmatch(o_raw)
        if m_lang:
            text, lang = m_lang.groups()
            g.add((s, p, Literal(text, lang=lang)))
            continue

        # ---------- 4B Data type literals ----------
        m_typed = LITERAL_TYPE_RE.fullmatch(o_raw)
        if m_typed:
            text, dt_uri, dt_curie = m_typed.groups()
            dt_full = dt_uri or expand_curie(dt_curie)

            if dt_full is None:
                print(f"⚠️  [skip] {csv_path.name}: unknown datatype '{dt_curie or dt_uri}'")
                continue

            # ---------- Special handling of dates ----------
            if dt_full == "http://www.w3.org/2001/XMLSchema#date" and re.fullmatch(r"\d{4}", text):
                # Automatically downgraded to gYear
                lit = Literal(text, datatype=URIRef("http://www.w3.org/2001/XMLSchema#gYear"))
            else:
                # Turn off normalization to avoid rdflib's failed conversion attempts
                lit = Literal(text, datatype=URIRef(dt_full), normalize=False)

            g.add((s, p, lit))
            continue
        
        if o_raw.startswith('"') and o_raw.endswith('"'):
            g.add((s, p, Literal(o_raw[1:-1], normalize=False)))
            continue

        # ---------- 4C Multi-value split (comma first) ----------
        if o_raw.strip().startswith("[") and o_raw.strip().endswith("]"):
            print(f"ℹ️  [skip] {csv_path.name}: blank-node expression not yet supported")
            continue

        chunks = [c.strip() for c in re.split(r'\s*,\s*(?=(?:<|https?://|[A-Za-z_][\w\-]*:))', o_raw) if c.strip()]
        added_any = False

        for chunk in chunks:
            # ① Contains spaces ⇒ Treated as normal literals
            if " " in chunk or "\n" in chunk:
                g.add((s, p, Literal(chunk, normalize=False)))
                added_any = True
                continue

            # ② Capturing URIs / Bare URIs / Angle bracket URIs
            m_uri = URI_INLINE_RE.fullmatch(chunk)
            if m_uri:
                uri_str = m_uri.group(1) or m_uri.group(0)
                g.add((s, p, URIRef(uri_str)))
                added_any = True
                continue

            # ③ Try treating the entire chunk as a CURIE
            full = expand_curie(chunk)
            if full:
                g.add((s, p, URIRef(full)))
                added_any = True
                continue

        # ④ Still not recognized - Issue warning
            print(f"⚠️  [skip] {csv_path.name}: unknown object token '{chunk}'")

        if not added_any:
            print(f"⚠️  [skip] {csv_path.name}: no valid object tokens in '{o_raw[:60]}…'")

# ------------------------------------------------------------------------
# 5. Main program
# ------------------------------------------------------------------------
def main() -> None:
    g_all = Graph()
    for pfx, uri in PREFIXES.items():
        g_all.bind(pfx, Namespace(uri))

    csv_files = [p for p in Path(".").glob("*.csv") if p.name != "prefixes.csv"]
    if not csv_files:
        print("‼️  No CSV files found.")
        return

    for csv_path in sorted(csv_files):
        print(f"🔄  Processing {csv_path.name}")
        csv_to_graph(csv_path, g_all)

    out_file = Path("combined.ttl")
    g_all.serialize(out_file, format="turtle")
    print(f"\n✅  DONE → {out_file.resolve()}  (triples: {len(g_all)})")

if __name__ == "__main__":
    main()
