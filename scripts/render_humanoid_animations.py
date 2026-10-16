"""Renders visual MP4 and animated GIF assets for the 3D humanoid simulation.

Generates:
1. Baseline erect walking locomotion (out/human_walk.mp4 & out/human_walk.gif)
2. Lidocaine-induced motor tone loss & postural buckling (out/human_lido.mp4 & out/human_lido.gif)
Copies visual artifacts into the brain conversation artifact folder.
"""

import os
import sys
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.human_pipeline import HumanPipelineSim

ARTIFACT_DIR = Path("/Users/shashwath/.gemini/antigravity-cli/brain/a6af1bbe-c9de-415f-b60b-cf2562665924")
OUT_DIR = Path("out")
OUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

def render_all():
    print("--- 1. Rendering Baseline Erect Walking Locomotion ---")
    sim_walk = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    walk_mp4 = str(OUT_DIR / "human_walk.mp4")
    walk_gif = str(OUT_DIR / "human_walk.gif")
    
    print(f"Rendering {walk_mp4}...")
    m_walk, _ = sim_walk.render_video(walk_mp4, duration=3.0, fps=25)
    sim_walk.close()
    
    # Also render GIF for showcase markdown
    print(f"Rendering {walk_gif}...")
    sim_walk_gif = HumanPipelineSim(drug_name=None, harness=True, harness_support=1.0)
    sim_walk_gif.render_video(walk_gif, duration=3.0, fps=20)
    sim_walk_gif.close()
    
    print(f"Walk metrics: Vx = {m_walk['body_metrics']['vx_m_s']:.3f} m/s, COM = {m_walk['body_metrics']['com_height_mean']:.3f} m")

    print("\n--- 2. Rendering Lidocaine Postural Buckling ---")
    sim_lido = HumanPipelineSim(drug_name="Lidocaine", harness=True, harness_support=1.0)
    lido_mp4 = str(OUT_DIR / "human_lido.mp4")
    lido_gif = str(OUT_DIR / "human_lido.gif")
    
    print(f"Rendering {lido_mp4}...")
    m_lido, _ = sim_lido.render_video(lido_mp4, duration=3.0, fps=25)
    sim_lido.close()
    
    print(f"Rendering {lido_gif}...")
    sim_lido_gif = HumanPipelineSim(drug_name="Lidocaine", harness=True, harness_support=1.0)
    sim_lido_gif.render_video(lido_gif, duration=3.0, fps=20)
    sim_lido_gif.close()
    
    print(f"Lidocaine metrics: Vx = {m_lido['body_metrics']['vx_m_s']:.3f} m/s, COM = {m_lido['body_metrics']['com_height_mean']:.3f} m")

    # Copy GIFs to artifact directory
    print("\n--- 3. Copying GIFs to Artifact Directory ---")
    shutil.copy(walk_gif, ARTIFACT_DIR / "human_walk.gif")
    shutil.copy(lido_gif, ARTIFACT_DIR / "human_lido.gif")
    print("Copied GIFs to", ARTIFACT_DIR)
    print("Render complete!")

if __name__ == "__main__":
    render_all()
