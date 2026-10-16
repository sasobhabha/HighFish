#!/usr/bin/env python3
"""Drug engine: resolve a user-facing product name to fly-level modulation.

Source of truth: data/pharmacology.yaml (all entries citation-keyed to
citations.md).
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
PHARM = ROOT_DIR / "data" / "pharmacology.yaml"


@lru_cache(maxsize=1)
def load_pharmacology() -> dict:
    with open(PHARM) as f:
        return yaml.safe_load(f)


def list_products() -> list[str]:
    return list(load_pharmacology()["products"].keys())


# Comprehensive synonyms and trade names mapping to canonical 17 pharmacology entries
ALIASES: dict[str, str] = {
    "dormiphen": "Dormiphen (Sleeping Pill)",
    "sleeping pill": "Dormiphen (Sleeping Pill)",
    "diphenhydramine": "Dormiphen (Sleeping Pill)",
    "diphenhydramine hcl": "Dormiphen (Sleeping Pill)",
    "benadryl": "Dormiphen (Sleeping Pill)",
    "claritin": "Claritin (Tablet)",
    "claritin tablet": "Claritin (Tablet)",
    "claritin gel": "Claritin (Gel)",
    "loratadine": "Claritin (Tablet)",
    "loratadine oral": "Claritin (Tablet)",
    "loratadine (oral)": "Claritin (Tablet)",
    "loratadine topical": "Claritin (Gel)",
    "loratadine (topical)": "Claritin (Gel)",
    "wellbutrin": "Bupropion (Wellbutrin)",
    "bupropion": "Bupropion (Wellbutrin)",
    "zyban": "Bupropion (Wellbutrin)",
    "tobacco": "Tobacco",
    "tobacco extract": "Tobacco Extract",
    "nicotine": "Tobacco",
    "nicotine leaf": "Tobacco",
    "nicotine (leaf)": "Tobacco",
    "nicotine extract": "Tobacco Extract",
    "nicotine (extract)": "Tobacco Extract",
    "gravol": "Dimenhydrinate (Gravol)",
    "dimenhydrinate": "Dimenhydrinate (Gravol)",
    "dramamine": "Dimenhydrinate (Gravol)",
    "robax": "Robax",
    "robaxin": "Robax",
    "methocarbamol": "Robax",
    "methocarbamol + ibuprofen": "Robax",
    "methocarbamol ibuprofen": "Robax",
    "weed": "Weed",
    "marijuana": "Weed",
    "cannabis": "Weed",
    "thc": "Weed",
    "delta-9-thc": "Weed",
    "delta 9 thc": "Weed",
    "delta-9-tetrahydrocannabinol": "Weed",
    "cbd": "CBD nanodrops",
    "cbd nanodrops": "CBD nanodrops",
    "cannabidiol": "CBD nanodrops",
    "cannabidiol (cbd)": "CBD nanodrops",
    "vyvanse": "Vyvanse",
    "lisdexamfetamine": "Vyvanse",
    "amphetamine": "Vyvanse",
    "adderall": "Vyvanse",
    "alcohol": "Jungle Juice (Everything mixed)",
    "ethanol": "Jungle Juice (Everything mixed)",
    "booze": "Jungle Juice (Everything mixed)",
    "jungle": "Jungle Juice (Everything mixed)",
    "jungle juice": "Jungle Juice (Everything mixed)",
    "multi compound": "Jungle Juice (Everything mixed)",
    "multi-compound": "Jungle Juice (Everything mixed)",
    "multi compound mixture": "Jungle Juice (Everything mixed)",
    "multi-compound mixture": "Jungle Juice (Everything mixed)",
    "multi-compound formulation": "Jungle Juice (Everything mixed)",
    "everything": "Jungle Juice (Everything mixed)",
    "all": "Jungle Juice (Everything mixed)",
    "lidocaine": "Lidocaine",
    "lido": "Lidocaine",
    "lithium": "Lithium Acetate",
    "lithium acetate": "Lithium Acetate",
    "acetaminophen": "Acetaminophen",
    "tylenol": "Acetaminophen",
    "paracetamol": "Acetaminophen",
    "mirtazapine": "Mirtazapine",
    "remeron": "Mirtazapine",
}

# Pure chemical names and active active ingredients (no commercial brand names)
CHEMICAL_NAMES: dict[str, str] = {
    "Caffeine": "Caffeine",
    "Claritin (Tablet)": "Loratadine (Oral)",
    "Claritin (Gel)": "Loratadine (Topical)",
    "Dormiphen (Sleeping Pill)": "Diphenhydramine",
    "Acetaminophen": "Acetaminophen",
    "Bupropion (Wellbutrin)": "Bupropion",
    "Tobacco": "Nicotine (Leaf)",
    "Tobacco Extract": "Nicotine (Extract)",
    "Dimenhydrinate (Gravol)": "Dimenhydrinate",
    "Lidocaine": "Lidocaine",
    "Lithium Acetate": "Lithium Acetate",
    "Mirtazapine": "Mirtazapine",
    "Weed": "Delta-9-THC",
    "CBD nanodrops": "Cannabidiol (CBD)",
    "Vyvanse": "Lisdexamfetamine",
    "Robax": "Methocarbamol + Ibuprofen",
    "Jungle Juice (Everything mixed)": "Multi-Compound Mixture",
}


def get_chemical_name(drug_name: str | None) -> str:
    """Returns pure chemical name / active compound without commercial brand names."""
    if not drug_name:
        return "Vehicle control"
    if drug_name in CHEMICAL_NAMES:
        return CHEMICAL_NAMES[drug_name]
    try:
        resolved = resolve_drug_name(drug_name)
        return CHEMICAL_NAMES.get(resolved, resolved)
    except Exception:
        return str(drug_name)


def get_brand_name(drug_name: str | None) -> str:
    """Returns canonical product / commercial brand name."""
    if not drug_name:
        return "Vehicle control"
    try:
        return resolve_drug_name(drug_name)
    except Exception:
        return str(drug_name)


def format_drug_name(drug_name: str | None, use_brand: bool = False) -> str:
    """Returns brand name if use_brand is True, else pure chemical name."""
    if use_brand:
        return get_brand_name(drug_name)
    return get_chemical_name(drug_name)



def resolve_drug_name(drug_name: str | None) -> str:
    """Resolves arbitrary user input (case-insensitive, trade name, slang) to canonical key."""
    if drug_name is None:
        return "Vehicle control"
    s = str(drug_name).strip().lower()
    if s in {"", "none", "vehicle", "control", "vehicle control", "placebo", "water"}:
        return "Vehicle control"

    ph = load_pharmacology()["products"]

    # 1. Exact match in canonical keys (case-insensitive)
    for p in ph:
        if s == p.lower():
            return p

    # 2. Exact match in aliases dictionary
    if s in ALIASES:
        target = ALIASES[s]
        if target in ph:
            return target

    # 3. Normalized punctuation / token matching
    s_clean = s.replace("-", " ").replace("(", "").replace(")", "").strip()
    if s_clean in ALIASES and ALIASES[s_clean] in ph:
        return ALIASES[s_clean]

    # 4. Substring containment in canonical keys
    for p in ph:
        if s in p.lower():
            return p

    # 5. Substring containment in aliases
    for alias, target in ALIASES.items():
        if s in alias and target in ph:
            return target

    raise KeyError(
        f"Unknown product '{drug_name}'. Valid products ({len(ph)}): {sorted(ph)}")


def drug_modulation(drug_name: str | None, dose: float = 1.0) -> dict:
    """Returns {product, cid, human, fly_mapping, sim_params, dose, citations}.

    dose in (0, 1] scales occupancy/gain parameters linearly (
    Hill-like model choice with n=1 per PDF Eq. 1; absolute concentrations
    are intentionally NOT claimed).
    """
    resolved = resolve_drug_name(drug_name)
    if resolved == "Vehicle control":
        return {"product": "Vehicle control", "cid": None, "human": None,
                "fly_mapping": {}, "sim_params": {}, "dose": 0.0, "citations": []}

    ph = load_pharmacology()["products"]
    entry = ph[resolved]
    sim_params = dict(entry.get("sim_params") or {})
    dose = float(np.clip(float(dose), 0.0, 1.0))
    for k, v in sim_params.items():
        if isinstance(v, (int, float)):
            sim_params[k] = v * dose
    return {
        "product": resolved,
        "cid": entry.get("cid"),
        "human": entry.get("human"),
        "fly_mapping": entry["fly"].get("mapping") or {},
        "fly_note": entry["fly"].get("note"),
        "sim_params": sim_params,
        "dose": dose,
        "citations": entry.get("human", {}).get("citations", [])
        + entry["fly"].get("citations", []),
    }


if __name__ == "__main__":
    prods = list_products()
    print(f"Total verified compounds: {len(prods)}")
    for name in prods:
        m = drug_modulation(name)
        print(f"  {get_chemical_name(name):34s} cid={str(m['cid']):>10s} "
              f"systems={sorted(m['fly_mapping'])}")

