#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_vallecupola_to_sample_ttl.py

"""

import re
from lxml import etree

def convert(xml_input_path: str, output_path: str = "ttl sample.ttl"):
    # 1. read and modify the prefix of xml:id 
    xml_text = open(xml_input_path, encoding="utf-8").read()
    fixed = re.sub(
        r'(xml:id=")(\d)',
        r'\1id_\2',
        xml_text
    )

    # 2. ANALYZE TEI/XML
    parser = etree.XMLParser(ns_clean=True, recover=True)
    root = etree.fromstring(fixed.encode("utf-8"), parser)
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    # 3. Collect scene ID sequence
    scenes = [
        div.get("{http://www.w3.org/XML/1998/namespace}id")
        for div in root.xpath('.//tei:div2[@type="scene"]', namespaces=ns)
    ]

    # 4. Document-level <rs> (not in any context and not starting with a number) as mentions
    story_mentions = []
    for rs in root.findall('.//tei:rs', namespaces=ns):
        rid = rs.get("{http://www.w3.org/XML/1998/namespace}id")
        # Check if it is in the scene
        parent = rs.getparent()
        while parent is not None and not (
            parent.tag == "{http://www.tei-c.org/ns/1.0}div2" and parent.get("type") == "scene"
        ):
            parent = parent.getparent()
        if parent is None and not re.match(r'^\d', rid):
            story_mentions.append(rid)

    # 5. Document-level <quote> (in div2 without type) as citation
    story_citations = [
        quote.get("{http://www.w3.org/XML/1998/namespace}id")
        for quote in root.xpath('.//tei:div2[not(@type)]//tei:quote', namespaces=ns)
    ]

    # 6. Mentions & citations for each scene
    scene_data = {}
    for div in root.xpath('.//tei:div2[@type="scene"]', namespaces=ns):
        sid = div.get("{http://www.w3.org/XML/1998/namespace}id")
        mentions, citations = [], []
        # <rs>
        for rs in div.findall('.//tei:rs', namespaces=ns):
            rid = rs.get("{http://www.w3.org/XML/1998/namespace}id")
            mentions.append(rid)
        # <placeName>
        for pn in div.findall(".//tei:placeName", namespaces=ns):
            pid = pn.get("{http://www.w3.org/XML/1998/namespace}id")
            if pid:
                mentions.append(pid)
        # <quote>
        for q in div.findall(".//tei:quote", namespaces=ns):
            citations.append(q.get("{http://www.w3.org/XML/1998/namespace}id"))
        scene_data[sid] = {"mentions": mentions, "citations": citations}

    # 7. Generate TTL text
    lines = []
    lines.append('@prefix val: <https://github.com/Vallecupola-Ecosystem/Exhibition/entities#> .')
    lines.append('@prefix schema: <https://schema.org/> .')
    lines.append('@prefix frbr: <http://purl.org/vocab/frbr/core#> .\n')

    # vallecupola_story block
    lines.append('val:vallecupola_story')
    # frbr:part
    for sid in scenes:
        lines.append(f'    frbr:part val:{sid} ;')
    # schema:mentions
    for mid in story_mentions:
        lines.append(f'    schema:mentions val:{mid} ;')
    # schema:citation
    for cid in story_citations:
        lines.append(f'    schema:citation val:{cid} ;')
    # Replace the ; at the end of the last line with .
    lines[-1] = lines[-1].rstrip(' ;') + ' .\n'

    # Each scene block
    for sid in scenes:
        data = scene_data.get(sid, {"mentions": [], "citations": []})
        lines.append(f'val:{sid}')
        # mentions
        for m in data["mentions"]:
            lines.append(f'    schema:mentions val:{m} ;')
        # citations (Finally move to next step)
        for c in data["citations"]:
            lines.append(f'    schema:citation val:{c} ;')
        # Replace the ; at the end of the last line with .
        lines[-1] = lines[-1].rstrip(' ;') + ' .\n'

    # 8. write file
    with open(output_path, 'w', encoding="utf-8") as f:
        f.write('\n'.join(lines))

    print(f"✅ Conversion completed, file:{output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("用法: python convert_vallecupola_to_sample_ttl.py <Vallecupola.xml>")
        sys.exit(1)
    convert(sys.argv[1])

# Example：
# cd /Users/yangtianchi/Downloads
# python3 convert_vallecupola_to_sample_ttl.py Vallecupola.xml
