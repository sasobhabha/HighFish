#!/usr/bin/env python3
"""Renders 3D humanoid biped walking videos (.mp4 and .gif) for all 17 canonical drugs + Vehicle Control.

Outputs high-definition tracking-camera footage with digital clinical HUD overlays.
"""

import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import imageio
import mujoco
import numpy as np
from PIL import Image, ImageDraw

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sim.drug_engine import (
    list_products,
    get_chemical_name,
    get_brand_name,
    drug_modulation,
)
from sim.human_pipeline import HumanPipelineSim, PHYSICS_DT


ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
OUT_DIR = ROOT_DIR / "out" / "videos" / "walking"


def draw_walking_hud(
    frame_rgb: np.ndarray,
    drug_name: str | None,
    dose: float,
    intent: Any,
    vx: float,
    t_sim: float,
) -> np.ndarray:
    """Renders scientific telemetry HUD over the humanoid walking camera frame."""
    img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size

    # 1. Top Header Banner (Translucent Dark Slate)
    draw.rectangle([0, 0, width, 52], fill=(15, 23, 42, 220))
    # Bottom Telemetry Bar
    draw.rectangle([0, height - 44, width, height], fill=(15, 23, 42, 225))

    tone = getattr(intent, "motor_tone", 1.0)
    mode = getattr(intent, "mode", "walk")

    # Status Badge Logic
    if tone < 0.35:
        badge_bg = (220, 38, 38, 235)      # Red Alert (Motor Blockade)
        badge_text = "MOTOR BLOCKADE / FLACCID"
    elif "sluggish" in mode or "sedated" in mode:
        badge_bg = (147, 51, 234, 230)     # Purple (Sedation)
        badge_text = "SEDATED / SLUGGISH GAIT"
    elif tone < 0.75:
        badge_bg = (217, 119, 6, 230)      # Amber (Hypotonic / Relaxed)
        badge_text = "HYPOTONIC / RELAXED"
    elif vx > 1.30:
        badge_bg = (14, 165, 233, 230)     # Sky Cyan (Hyperactive)
        badge_text = "HYPERACTIVE / ACCELERATED"
    else:
        badge_bg = (34, 197, 94, 230)      # Emerald (Normal Walk)
        badge_text = "NORMAL STEADY BIPED GAIT"

    chem_name = get_chemical_name(drug_name) if drug_name else "Vehicle control (Baseline)"
    draw.text((16, 12), f"SPEED: {vx:4.2f} m/s", fill=(255, 255, 255), font_size=16)
    draw.text((170, 14), f"COMPOUND: {chem_name} ({dose:.1f})", fill=(203, 213, 225), font_size=14)

    # Status Badge (Top Right)
    badge_w = 240
    draw.rounded_rectangle([width - badge_w - 12, 8, width - 12, 44], radius=6, fill=badge_bg)
    draw.text((width - badge_w + 10, 14), badge_text, fill=(255, 255, 255), font_size=12)

    # Bottom Instrument Cluster
    cadence = getattr(intent, "cadence", 1.0)
    stride = getattr(intent, "stride_length", 0.6)
    coord = getattr(intent, "coordination", 1.0)

    y_bot = height - 30
    col1 = f"T: {t_sim:4.2f}s"
    col2 = f"CADENCE: {cadence:4.2f} Hz"
    col3 = f"STRIDE: {stride:4.2f}m"
    col4 = f"TONE: {tone:4.2f}"
    col5 = f"COORD: {coord:4.2f}"

    draw.text((16, y_bot), col1, fill=(56, 189, 248), font_size=13)
    draw.text((110, y_bot), col2, fill=(244, 114, 182), font_size=13)
    draw.text((260, y_bot), col3, fill=(250, 204, 21), font_size=13)
    draw.text((410, y_bot), col4, fill=(74, 222, 128), font_size=13)
    draw.text((520, y_bot), col5, fill=(226, 232, 240), font_size=13)

    return np.array(img)


def render_walking_video(
    drug_name: str | None,
    out_prefix: str,
    duration: float = 2.5,
    fps: int = 25,
) -> dict:
    """Renders a single drug walking trial to MP4 and GIF with HUD overlay."""
    sim = HumanPipelineSim(drug_name=drug_name, dose=1.0)
    renderer = mujoco.Renderer(sim.body.mj_model, height=480, width=640)

    n_steps = int(np.ceil(duration / PHYSICS_DT))
    render_interval = max(1, int(round(1.0 / (fps * PHYSICS_DT))))
    frames = []

    for _ in range(40):
        sim.neural.step()

    intent = sim.translator.translate(sim.neural, sim.mod, sim.stim_mgr)
    x_prev = sim.body.mj_data.xpos[sim.body.pelvis_id][0]

    for step_idx in range(n_steps):
        t_sim = step_idx * PHYSICS_DT
        curr_pos = sim.body.mj_data.xpos[sim.body.pelvis_id]
        pos_mm = np.array([curr_pos[0] * 1000.0, curr_pos[1] * 1000.0, 0.0])
        fwd_vec = np.array([1.0, 0.0, 0.0])

        stim_signals = sim.stim_mgr.update(
            t=t_sim,
            fly_pos=pos_mm,
            fly_forward=fwd_vec,
            dn_drive=sim.last_drive,
        )
        sim.neural.apply_stim(
            food_gain=stim_signals.get("food_gain", 0.0),
            predator_intensity=stim_signals.get("predator_intensity", 0.0),
            turn_bias=stim_signals.get("turn_bias", 0.0),
        )

        if step_idx % 10 == 0:
            sim.neural.step()
            r_dn = float(np.mean(sim.neural.r[sim.translator.all_dn_idx]))
            sim.last_drive = r_dn
            intent = sim.translator.translate(sim.neural, sim.mod, sim.stim_mgr)

        phi_l, phi_r = sim.cpg.step(PHYSICS_DT, intent)
        joint_targets = sim.kin.compute_joint_targets(PHYSICS_DT, phi_l, phi_r, intent)

        sim.body.harness_support = sim.harness_support * float(np.clip(intent.posture_height, 0.2, 1.0))
        sim.body.step(joint_targets)

        if step_idx % render_interval == 0:
            renderer.update_scene(sim.body.mj_data, camera="trackcam")
            raw_rgb = renderer.render()
            x_now = sim.body.mj_data.xpos[sim.body.pelvis_id][0]
            dt_step = (render_interval * PHYSICS_DT)
            inst_vx = max(0.0, (x_now - x_prev) / dt_step) if step_idx > 0 else 0.0
            x_prev = x_now
            hud_frame = draw_walking_hud(raw_rgb, drug_name, 1.0, intent, inst_vx, t_sim)
            frames.append(hud_frame)

    metrics = sim.body.get_metrics()
    sim.close()

    mp4_path = f"{out_prefix}.mp4"
    gif_path = f"{out_prefix}.gif"

    Path(mp4_path).parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(mp4_path, frames, fps=fps)
    imageio.mimsave(gif_path, frames, fps=fps, loop=0)

    # Also save to artifact directory if available
    artifact_mp4 = ARTIFACT_DIR / Path(mp4_path).name
    artifact_gif = ARTIFACT_DIR / Path(gif_path).name
    imageio.mimsave(str(artifact_mp4), frames, fps=fps)
    imageio.mimsave(str(artifact_gif), frames, fps=fps, loop=0)

    return {
        "mp4": str(mp4_path),
        "gif": str(gif_path),
        "artifact_mp4": str(artifact_mp4),
        "artifact_gif": str(artifact_gif),
        "frames": len(frames),
        "mean_vx": round(metrics.get("vx_m_s", 0.0), 3),
        "fall_detected": metrics.get("fall_detected", False),
    }


def render_all_walking_videos():
    products = list_products()
    test_conditions = [("Vehicle control", None)] + [(p, p) for p in products]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    print("=================================================================")
    print(f"  RENDERING 3D HUMANOID WALKING VIDEOS ({len(test_conditions)} CONDITIONS)")
    print("=================================================================\n")

    catalog = []
    t_start = time.time()

    for idx, (label, drug_arg) in enumerate(test_conditions, 1):
        clean_tag = label.split("(")[0].strip().lower().replace(" ", "_").replace("+", "plus").replace("-", "_")
        prefix = OUT_DIR / f"walk_{idx:02d}_{clean_tag}"
        chem_name = get_chemical_name(drug_arg) if drug_arg else "Vehicle control (Baseline)"
        brand_name = get_brand_name(drug_arg) if drug_arg else "Vehicle control"

        print(f"[{idx:2d}/{len(test_conditions):2d}] Rendering {chem_name} (Brand: {brand_name})...", end="", flush=True)
        t0 = time.time()
        res = render_walking_video(drug_name=drug_arg, out_prefix=str(prefix), duration=2.5, fps=25)
        elapsed = time.time() - t0
        print(f" DONE in {elapsed:.2f}s | Speed: {res['mean_vx']:.2f} m/s | Saved: {Path(res['mp4']).name}")

        catalog.append({
            "index": idx,
            "label": label,
            "chemical_name": chem_name,
            "brand_name": brand_name,
            "mean_vx": res["mean_vx"],
            "mp4": res["mp4"],
            "gif": res["gif"],
            "artifact_mp4": res["artifact_mp4"],
            "artifact_gif": res["artifact_gif"],
        })

    total_time = time.time() - t_start
    print(f"\nSuccessfully rendered all {len(catalog)} walking videos in {total_time:.2f}s!")

    # Generate Gallery Markdown Document
    gallery_md = generate_gallery_markdown(catalog)
    gallery_path = OUT_DIR / "WALKING_VIDEOS_GALLERY.md"
    gallery_path.write_text(gallery_md, encoding="utf-8")
    (ARTIFACT_DIR / "WALKING_VIDEOS_GALLERY.md").write_text(gallery_md, encoding="utf-8")
    print(f"Gallery Markdown generated at: {gallery_path}")
    print(f"Artifact Gallery generated at: {ARTIFACT_DIR / 'WALKING_VIDEOS_GALLERY.md'}")

    # Generate Index JSON
    index_json = OUT_DIR / "walking_videos_index.json"
    with open(index_json, "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2)
    print(f"Index JSON saved to: {index_json}")

    return catalog


def generate_gallery_markdown(catalog: list[dict]) -> str:
    lines = [
        "# 3D Humanoid Locomotion Video Gallery: All 17 Drugs + Vehicle Control",
        "",
        "This gallery presents offscreen MuJoCo 3D tracking-camera video recordings of the biped humanoid locomotion model driven by the FlyWire v783 connectome (139,255 neurons | 1,305 DNs) for all canonical drugs and baseline vehicle control.",
        "",
        "Each video features a real-time clinical HUD displaying instant forward speed, cadence, stride length, motor tone, and gait state.",
        "",
        "---",
        "",
        "## Quick Navigation Index",
        "",
        "| # | Compound (Chemical) | Brand Name | Biped Speed ($v_x$) | Video File (.mp4) | Animation (.gif) |",
        "|---|---|---|---|---|---|",
    ]

    for c in catalog:
        mp4_name = Path(c["mp4"]).name
        gif_name = Path(c["gif"]).name
        lines.append(
            f"| {c['index']} | **{c['chemical_name']}** | *{c['brand_name']}* | `{c['mean_vx']:.2f} m/s` | [{mp4_name}]({c['artifact_mp4']}) | [{gif_name}]({c['artifact_gif']}) |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Individual Locomotion Video Showcases",
        "",
    ])

    for c in catalog:
        lines.extend([
            f"### {c['index']}. {c['chemical_name']} (*{c['brand_name']}*)",
            f"- **Forward Locomotion Speed**: `{c['mean_vx']:.2f} m/s`",
            f"- **MP4 Video**: [{Path(c['mp4']).name}]({c['artifact_mp4']})",
            f"- **GIF Animation**: [{Path(c['gif']).name}]({c['artifact_gif']})",
            "",
            f"![{c['chemical_name']} Walking Animation]({c['artifact_gif']})",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


if __name__ == "__main__":
    render_all_walking_videos()
