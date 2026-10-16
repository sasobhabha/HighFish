#!/usr/bin/env python3
"""Verify compound identities via PubChem PUG REST.

Policy: a CID is recorded ONLY if the API returns it. If a compound is not found
or is ambiguous, it is recorded with an explicit status instead of a guessed CID.
Every user-facing product name is mapped to the active molecule(s) it contains;
the mapping itself is justified by the citations in citations.md.
"""
import json
import time
import urllib.parse
import urllib.request

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name"

# product -> list of active molecules to verify
COMPOUNDS = {
    "Caffeine": ["caffeine"],
    "Pepto Bismol": ["bismuth subsalicylate"],
    "Claritin (Tablet)": ["loratadine"],
    "Claritin (Gel)": ["loratadine"],
    "Codeine": ["codeine"],
    "Dormiphen (Sleeping Pill)": ["diphenhydramine"],
    "Acetaminophen": ["acetaminophen"],
    "Bupropion (Wellbutrin)": ["bupropion"],
    "Tobacco": ["nicotine"],
    "Tobacco Extract": ["nicotine"],
    "Dimenhydrinate (Gravol)": ["dimenhydrinate", "diphenhydramine", "8-chlorotheophylline"],
    "Fexofenadine (Allegra)": ["fexofenadine"],
    "Lidocaine": ["lidocaine"],
    "Lithium Acetate": ["lithium acetate", "lithium"],
    "Melatonin": ["melatonin"],
    "Mirtazapine": ["mirtazapine"],
    "Famotidine (Pepcid)": ["famotidine"],
    "Pregabalin (Lyrica)": ["pregabalin"],
    "Weed": ["delta-9-tetrahydrocannabinol", "cannabidiol"],
    "THCa nanodrops": ["tetrahydrocannabinolic acid"],
    "CBD nanodrops": ["cannabidiol"],
    "Vyvanse": ["lisdexamfetamine"],
    "Robax": ["ibuprofen", "methocarbamol"],
    "Naproxen": ["naproxen"],
    "Mometasone (Nasonex)": ["mometasone furoate"],
    "Ibuprofen": ["ibuprofen"],
}


def cid_for_name(name: str):
    url = f"{BASE}/{urllib.parse.quote(name)}/cids/JSON"
    req = urllib.request.Request(url, headers={"User-Agent": "HighFly-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        cids = data.get("IdentifierList", {}).get("CID", [])
        return {"status": "ok", "cids": cids}
    except Exception as e:  # noqa: BLE001 - record the failure
        return {"status": f"error: {type(e).__name__}", "cids": []}


def props_for_cid(cid: int):
    url = (
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/"
        f"{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,Title/JSON"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "HighFly-research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
        p = data["PropertyTable"]["Properties"][0]
        return {
            "title": p.get("Title"),
            "formula": p.get("MolecularFormula"),
            "mw": p.get("MolecularWeight"),
            "smiles": p.get("CanonicalSMILES"),
        }
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}"}


def main():
    out = {"retrieved": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "compounds": {}}
    for product, mols in COMPOUNDS.items():
        entry = {}
        for mol in mols:
            res = cid_for_name(mol)
            if res["cids"]:
                first = res["cids"][0]
                res["primary_cid"] = first
                res["properties"] = props_for_cid(first)
                time.sleep(0.25)
            entry[mol] = res
            print(f"{product:32s} {mol:38s} -> {res['status']} "
                  f"cids={res['cids'][:3]}{'...' if len(res['cids']) > 3 else ''}")
            time.sleep(0.25)
        out["compounds"][product] = entry
    with open("data/pubchem_cids.json", "w") as f:
        json.dump(out, f, indent=2)
    n_ok = sum(
        1 for p in out["compounds"].values() for m in p.values() if m["status"] == "ok"
    )
    n_tot = sum(len(p) for p in out["compounds"].values())
    print(f"\n{n_ok}/{n_tot} compound lookups returned a CID "
          f"(source: pubchem.ncbi.nlm.nih.gov PUG REST)")


if __name__ == "__main__":
    main()
