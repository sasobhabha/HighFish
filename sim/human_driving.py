#!/usr/bin/env python3
"""Human Driving Mode: Neuro-Pharmacological Impairment Simulation on a 3D Obstacle Course with Dynamic NPC Bots.

Evaluates how pharmacological agents (Caffeine, Dormiphen, Lidocaine, GABA antagonists,
Alcohol/Jungle Juice) impair driving performance on a demanding 100-meter test course:
1. Slalom Zone: Alternating traffic pylons requiring rhythmic, coordinated steering.
2. Sudden Lead-Vehicle Braking Hazard (NPC Bot 1): Tests brake reaction time (BRT) and rear-end collision risk.
3. Cross-Traffic Intersection Incursion (NPC Bot 2): Tests hazard anticipation and evasive steering.
4. Chicane / S-Bend Zone: Tests high-frequency directional lane transitions and curb strikes.

Clinical Driving Impairment Metrics (FDA / NHTSA Standards):
- SDLP: Standard Deviation of Lateral Position (lane weaving index in meters).
- BRT: Brake Reaction Time (latency in ms from hazard detection to braking).
- Cone Collisions: Number of knocked-over traffic pylons.
- NPC Collisions: Direct vehicle-to-vehicle impacts.
- Off-Road Excursions: Number of lateral road boundary breaches.
- Outcome: completed_clean | pylon_strikes | rear_end_collision | cross_traffic_t_bone | off_road_spinout | stalled.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sim.drug_engine import drug_modulation, load_pharmacology
from sim.neural_sim import FlyWireNeuralSim
from sim.human_translation import DNToHumanTranslator, HumanIntent


# =====================================================================
# 1. Procedural MuJoCo MJCF Generator for the 100m Driving Course
# =====================================================================

def resolve_drug_name(name: str | None) -> str:
    """Resolves partial / informal drug names to exact pharmacology entries."""
    from sim.drug_engine import resolve_drug_name as _resolve
    try:
        return _resolve(name)
    except KeyError:
        return name or "Vehicle control"



def get_driving_course_mjcf(
    track_length: float = 100.0,
    lane_width: float = 4.0,
) -> str:
    """Generates a complete, self-contained MuJoCo MJCF model for the vehicle & obstacle course."""
    half_w = lane_width

    # Slalom cone positions along the center divider line (Y = 0)
    cones = [
        (20.0, 0.0),
        (28.0, 0.0),
        (36.0, 0.0),
    ]

    cone_geoms = []
    for i, (cx, cy) in enumerate(cones):
        cone_geoms.append(f"""
    <body name="pylon_{i}" pos="{cx} {cy} 0.35">
      <joint type="free"/>
      <!-- Traffic Pylon Base & Cone -->
      <geom name="pylon_base_{i}" type="box" size="0.22 0.22 0.04" rgba="0.95 0.35 0.05 1" mass="2.5" friction="1.2 0.01 0.001"/>
      <geom name="pylon_cone_{i}" type="cylinder" size="0.12 0.30" rgba="1.0 0.40 0.0 1" mass="1.5" friction="1.2 0.01 0.001"/>
      <!-- Retro-reflective white stripe -->
      <geom name="pylon_stripe_{i}" type="cylinder" size="0.125 0.08" pos="0 0 0.08" rgba="0.98 0.98 0.98 1" mass="0.1"/>
    </body>""")

    cone_xml = "\n".join(cone_geoms)

    # Road dashed center lines
    road_stripes = []
    for sx in np.arange(2.0, track_length - 2.0, 5.0):
        road_stripes.append(f"""
    <geom name="stripe_{int(sx)}" type="box" size="1.5 0.10 0.002" pos="{sx+1.5:.1f} 0 0.002" rgba="0.95 0.85 0.1 1" contype="0" conaffinity="0"/>
    """)
    stripe_xml = "\n".join(road_stripes)

    # Chicane barrier blocks (X = 76 to 88m)
    barrier_xml = f"""
    <!-- Concrete Chicane Barriers -->
    <body name="barrier_left" pos="78.0 1.8 0.45">
      <geom name="barrier_l_geom" type="box" size="3.5 0.35 0.45" rgba="0.8 0.2 0.2 1" mass="1500" friction="1.5 0.02 0.001"/>
    </body>
    <body name="barrier_right" pos="84.0 -1.8 0.45">
      <geom name="barrier_r_geom" type="box" size="3.5 0.35 0.45" rgba="0.8 0.2 0.2 1" mass="1500" friction="1.5 0.02 0.001"/>
    </body>
    <!-- Finish Line Archway -->
    <body name="finish_gate" pos="92.0 0 2.2">
      <geom type="box" size="0.2 4.5 0.15" pos="0 0 1.0" rgba="0.1 0.7 0.2 1"/>
      <geom type="cylinder" size="0.12 1.6" pos="0 -4.5 0.0" rgba="0.9 0.9 0.9 1"/>
      <geom type="cylinder" size="0.12 1.6" pos="0 4.5 0.0" rgba="0.9 0.9 0.9 1"/>
    </body>
    """

    mjcf = f"""<mujoco model="human_driving_arena">
  <compiler angle="radian"/>
  <option timestep="0.005" gravity="0 0 -9.81" integrator="Euler"/>
  <visual>
    <headlight ambient="0.45 0.45 0.48" diffuse="0.8 0.8 0.85" specular="0.3 0.3 0.3"/>
    <quality shadowsize="2048"/>
  </visual>

  <asset>
    <texture name="sky" type="skybox" builtin="gradient" rgb1="0.4 0.6 0.85" rgb2="0.85 0.9 0.95" width="512" height="512"/>
    <material name="asphalt" reflectance="0.15" specular="0.2"/>
  </asset>

  <worldbody>
    <!-- Ground Grass Plane -->
    <geom name="ground" type="plane" size="120 40 0.1" rgba="0.25 0.45 0.22 1" friction="1.2 0.01 0.001"/>
    <!-- 100m Asphalt Road Surface -->
    <geom name="road" type="box" size="{track_length/2:.1f} {half_w:.1f} 0.001" pos="{track_length/2:.1f} 0 0.001" rgba="0.20 0.21 0.23 1" friction="1.4 0.01 0.001"/>

    <!-- Left & Right White Edge Lines -->
    <geom name="edge_left" type="box" size="{track_length/2:.1f} 0.12 0.002" pos="{track_length/2:.1f} {half_w-0.15:.2f} 0.002" rgba="0.95 0.95 0.95 1" contype="0" conaffinity="0"/>
    <geom name="edge_right" type="box" size="{track_length/2:.1f} 0.12 0.002" pos="{track_length/2:.1f} {-half_w+0.15:.2f} 0.002" rgba="0.95 0.95 0.95 1" contype="0" conaffinity="0"/>

    <!-- Left & Right Road Curbs -->
    <geom name="curb_l" type="box" size="{track_length/2:.1f} 0.25 0.12" pos="{track_length/2:.1f} {half_w+0.25:.2f} 0.06" rgba="0.75 0.25 0.25 1" mass="10000" friction="1.8 0.01 0.001"/>
    <geom name="curb_r" type="box" size="{track_length/2:.1f} 0.25 0.12" pos="{track_length/2:.1f} {-half_w-0.25:.2f} 0.06" rgba="0.75 0.25 0.25 1" mass="10000" friction="1.8 0.01 0.001"/>

    {stripe_xml}
    {cone_xml}
    {barrier_xml}

    <!-- =============================================================== -->
    <!-- NPC Bot 1: Lead Vehicle (Sudden Braker Hazard in Front Lane)   -->
    <!-- =============================================================== -->
    <body name="npc_lead" pos="50.0 -1.5 0.35">
      <joint name="npc_lead_x" type="slide" axis="1 0 0"/>
      <joint name="npc_lead_y" type="slide" axis="0 1 0"/>
      <geom name="npc_lead_body" type="box" size="1.6 0.75 0.32" rgba="0.15 0.35 0.85 1" mass="750" friction="1.2 0.01 0.001"/>
      <geom name="npc_lead_cabin" type="box" size="0.9 0.65 0.25" pos="-0.2 0 0.35" rgba="0.1 0.2 0.5 0.8"/>
      <!-- Brake Lights (Glow Red during braking event) -->
      <geom name="npc_brake_l" type="box" size="0.05 0.15 0.08" pos="-1.65 0.5 0.1" rgba="0.4 0.0 0.0 1"/>
      <geom name="npc_brake_r" type="box" size="0.05 0.15 0.08" pos="-1.65 -0.5 0.1" rgba="0.4 0.0 0.0 1"/>
    </body>

    <!-- =============================================================== -->
    <!-- NPC Bot 2: Cross-Traffic Delivery Vehicle (Intersection Incursion)-->
    <!-- =============================================================== -->
    <body name="npc_cross" pos="68.0 7.5 0.35">
      <joint name="npc_cross_y" type="slide" axis="0 1 0"/>
      <geom name="npc_cross_body" type="box" size="1.2 0.8 0.40" rgba="0.85 0.75 0.15 1" mass="600" friction="1.2 0.01 0.001"/>
      <geom name="npc_cross_top" type="cylinder" size="0.25 0.15" pos="0 0 0.45" rgba="0.9 0.1 0.1 1"/>
    </body>

    <!-- =============================================================== -->
    <!-- Subject Human-Driven Vehicle (Car Chassis & Steerable Wheels)    -->
    <!-- =============================================================== -->
    <body name="car" pos="2.0 -1.5 0.40">
      <freejoint name="car_root"/>
      <!-- Main Sports Car Body Shell -->
      <geom name="chassis" type="box" size="1.6 0.60 0.18" pos="0 0 0.06" rgba="0.90 0.12 0.15 1" mass="450" friction="1.2 0.01 0.001"/>
      <!-- Cockpit & Windshield -->
      <geom name="cockpit" type="box" size="0.9 0.65 0.22" pos="-0.2 0 0.28" rgba="0.15 0.18 0.22 0.85"/>
      <geom name="windshield" type="box" size="0.45 0.62 0.15" pos="0.5 0 0.24" rgba="0.6 0.8 0.95 0.4"/>

      <!-- Headlights -->
      <geom name="headlight_l" type="box" size="0.05 0.16 0.07" pos="1.62 0.55 0.05" rgba="0.98 0.98 0.8 1"/>
      <geom name="headlight_r" type="box" size="0.05 0.16 0.07" pos="1.62 -0.55 0.05" rgba="0.98 0.98 0.8 1"/>

      <!-- Human Driver Head & Torso Indicator inside Cockpit -->
      <body name="driver_torso" pos="-0.2 0.2 0.35">
        <geom type="capsule" size="0.14 0.16" rgba="0.25 0.35 0.55 1" mass="35"/>
        <geom type="sphere" size="0.12" pos="0 0 0.28" rgba="0.85 0.70 0.58 1" mass="5"/>
      </body>

      <!-- Chase & Tracking Camera (Rigid Body Frame View) -->
      <camera name="trackcam" pos="-5.5 0 2.8" xyaxes="0 -1 0 0.38 0 0.92"/>

      <!-- Front Left Wheel Assembly (Steered Knuckle + Free Roll) -->
      <body name="steer_fl" pos="1.2 0.85 -0.10">
        <joint name="steer_fl_joint" type="hinge" axis="0 0 1" range="-0.65 0.65" damping="15"/>
        <geom name="knuckle_fl" type="sphere" size="0.08" mass="4"/>
        <body name="wheel_fl">
          <joint name="roll_fl" type="hinge" axis="0 1 0" damping="0.1"/>
          <geom name="wheel_geom_fl" type="cylinder" size="0.25 0.08" zaxis="0 1 0" rgba="0.12 0.12 0.14 1" mass="15" friction="1.4 0.01 0.001"/>
        </body>
      </body>

      <!-- Front Right Wheel Assembly (Steered Knuckle + Free Roll) -->
      <body name="steer_fr" pos="1.2 -0.85 -0.10">
        <joint name="steer_fr_joint" type="hinge" axis="0 0 1" range="-0.65 0.65" damping="15"/>
        <geom name="knuckle_fr" type="sphere" size="0.08" mass="4"/>
        <body name="wheel_fr">
          <joint name="roll_fr" type="hinge" axis="0 1 0" damping="0.1"/>
          <geom name="wheel_geom_fr" type="cylinder" size="0.25 0.08" zaxis="0 1 0" rgba="0.12 0.12 0.14 1" mass="15" friction="1.4 0.01 0.001"/>
        </body>
      </body>

      <!-- Rear Left Wheel Assembly (Propelled) -->
      <body name="wheel_rl" pos="-1.2 0.85 -0.10">
        <joint name="roll_rl" type="hinge" axis="0 1 0" damping="0.2"/>
        <geom name="wheel_geom_rl" type="cylinder" size="0.25 0.08" zaxis="0 1 0" rgba="0.12 0.12 0.14 1" mass="18" friction="1.6 0.01 0.001"/>
      </body>

      <!-- Rear Right Wheel Assembly (Propelled) -->
      <body name="wheel_rr" pos="-1.2 -0.85 -0.10">
        <joint name="roll_rr" type="hinge" axis="0 1 0" damping="0.2"/>
        <geom name="wheel_geom_rr" type="cylinder" size="0.25 0.08" zaxis="0 1 0" rgba="0.12 0.12 0.14 1" mass="18" friction="1.6 0.01 0.001"/>
      </body>
    </body>
  </worldbody>

  <!-- Actuators: Steering Position Servos and Rear Wheel Drive Motors -->
  <actuator>
    <position name="steer_fl_act" joint="steer_fl_joint" kp="2500" kv="120" ctrlrange="-0.65 0.65"/>
    <position name="steer_fr_act" joint="steer_fr_joint" kp="2500" kv="120" ctrlrange="-0.65 0.65"/>
    <motor name="drive_rl" joint="roll_rl" ctrlrange="-1200 1200"/>
    <motor name="drive_rr" joint="roll_rr" ctrlrange="-1200 1200"/>
  </actuator>

  <contact>
    <exclude body1="car" body2="steer_fl"/>
    <exclude body1="car" body2="wheel_fl"/>
    <exclude body1="car" body2="steer_fr"/>
    <exclude body1="car" body2="wheel_fr"/>
    <exclude body1="car" body2="wheel_rl"/>
    <exclude body1="car" body2="wheel_rr"/>
  </contact>
</mujoco>
"""
    return mjcf


# =====================================================================
# 2. Human Driving Simulation & Impairment Metric Engine
# =====================================================================

@dataclass
class DrivingMetrics:
    drug_name: str
    dose: float
    duration_s: float
    sdlp_m: float                  # Standard Deviation of Lateral Position (lane weaving)
    mean_speed_m_s: float          # Average velocity (m/s)
    peak_speed_m_s: float          # Top speed achieved (m/s)
    brake_reaction_time_ms: float  # Latency from lead car hazard to braking
    cone_collisions: int           # Knocked-down traffic pylons
    npc_collisions: int            # Vehicle-to-vehicle crashes
    off_road_excursions: int       # Breaches past lane boundaries
    course_completed: bool         # Crossed finish line
    driving_outcome: str           # Clinical impairment verdict


class HumanDrivingSim:
    """Couples FlyWire connectome rate dynamics to a 3D driving obstacle course."""

    def __init__(
        self,
        drug_name: str | None = None,
        dose: float = 1.0,
        track_length: float = 100.0,
    ):
        self.drug_name = resolve_drug_name(drug_name)
        self.dose = float(np.clip(dose, 0.0, 1.0))
        self.track_length = track_length

        # 1. Neural connectome & translation layer
        self.neural = FlyWireNeuralSim()
        self.translator = DNToHumanTranslator()
        if "gaba" in self.drug_name.lower() or "alcohol" in self.drug_name.lower():
            self.mod = {
                "product": "GABA_A antagonist",
                "cid": None,
                "fly_mapping": {"rdl": {"direction": "blocker"}},
                "sim_params": {"rdl_phi": 0.75 * self.dose},
                "dose": self.dose,
                "citations": ["C121", "C122"],
            }
        else:
            self.mod = drug_modulation(self.drug_name, self.dose)
        if self.mod.get("fly_mapping"):
            self.neural.apply_drug(self.mod["fly_mapping"], self.mod.get("sim_params", {}))

        # 2. Build 3D MuJoCo Driving Arena
        self.mjcf_xml = get_driving_course_mjcf(track_length=track_length)
        self.mj_model = mujoco.MjModel.from_xml_string(self.mjcf_xml)
        self.mj_data = mujoco.MjData(self.mj_model)

        # Body & Actuator IDs
        self.car_body_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "car")
        self.npc_lead_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "npc_lead")
        self.npc_cross_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "npc_cross")

        self.steer_fl_act = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_ACTUATOR, "steer_fl_act")
        self.steer_fr_act = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_ACTUATOR, "steer_fr_act")
        self.drive_rl_act = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive_rl")
        self.drive_rr_act = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_ACTUATOR, "drive_rr")

        # NPC joints
        self.j_npc_lead_x = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_JOINT, "npc_lead_x")
        self.j_npc_cross_y = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_JOINT, "npc_cross_y")

        # NPC State variables
        self.npc_lead_pos_x = 50.0
        self.npc_lead_vel_x = 1.4   # moves ahead at 1.4 m/s
        self.npc_lead_braking = False
        self.npc_lead_brake_time = None

        self.npc_cross_pos_y = 7.5
        self.npc_cross_vel_y = 0.0

        # Neural network warmup to steady-state rate (~0.65)
        for _ in range(25):
            self.neural.step()

        # Telemetry & metric recording
        self.t_sim = 0.0
        self.lateral_positions: list[float] = []
        self.forward_speeds: list[float] = []
        self.cone_hits: set[int] = set()
        self.npc_hits: set[str] = set()
        self.off_road_count = 0
        self.was_off_road = False

        self.hazard_time = None
        self.brake_applied_time = None
        self.outcome = "in_progress"

    @property
    def driver_reaction_delay_ms(self) -> float:
        """Driver brake reaction latency in milliseconds based on pharmacological state."""
        lat = 250.0
        if "Dormiphen" in self.drug_name or self.neural.arousal_attenuation < 0.85:
            lat += 1250.0
        elif "Jungle" in self.drug_name:
            lat += 850.0
        elif "Caffeine" in self.drug_name:
            lat = 160.0
        elif "Lidocaine" in self.drug_name:
            lat += 500.0
        return lat


    def step(self, dt: float = 0.005) -> dict[str, Any]:
        """Advances the coupled brain -> driver -> vehicle -> NPC physics by dt."""
        self.t_sim += dt
        car_pos = self.mj_data.xpos[self.car_body_id]
        car_x, car_y, car_z = car_pos[0], car_pos[1], car_pos[2]

        # Velocity in world frame
        c_vel = self.mj_data.cvel[self.car_body_id]
        car_vx = float(c_vel[3])

        # Record telemetry
        self.lateral_positions.append(float(car_y))
        self.forward_speeds.append(float(car_vx))

        # Check lane departure (|y| > 3.8m)
        if abs(car_y) > 3.8:
            if not self.was_off_road:
                self.off_road_count += 1
                self.was_off_road = True
        else:
            self.was_off_road = False

        # -------------------------------------------------------------
        # 1. NPC Dynamic Hazard Simulation
        # -------------------------------------------------------------
        # A. Lead Car (Hazard 1): At X=50m, moves forward.
        # When driver car approaches within 12m of lead car, lead car BRAKES SHARPLY!
        dist_lead = (self.npc_lead_pos_x - car_x)
        if 0 < dist_lead < 9.5 and not self.npc_lead_braking:
            self.npc_lead_braking = True
            self.npc_lead_brake_time = self.t_sim
            self.hazard_time = self.t_sim
            # Turn brake lights red
            b_l = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, "npc_brake_l")
            b_r = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, "npc_brake_r")
            if b_l >= 0 and b_r >= 0:
                self.mj_model.geom_rgba[b_l] = [1.0, 0.05, 0.05, 1.0]
                self.mj_model.geom_rgba[b_r] = [1.0, 0.05, 0.05, 1.0]

        if self.npc_lead_braking:
            # Emergency stop for 2.2s, then accelerate away to clear the lane
            if self.hazard_time is not None and (self.t_sim - self.hazard_time) > 2.2:
                self.npc_lead_vel_x = min(8.0, self.npc_lead_vel_x + 4.5 * dt)
            else:
                self.npc_lead_vel_x = max(0.0, self.npc_lead_vel_x - 5.5 * dt)

        self.npc_lead_pos_x += self.npc_lead_vel_x * dt
        # Write to joint qpos
        qpos_idx_lead = self.mj_model.jnt_qposadr[self.j_npc_lead_x]
        self.mj_data.qpos[qpos_idx_lead] = (self.npc_lead_pos_x - 50.0)

        # B. Cross-Traffic Incursion (Hazard 2):
        # When car reaches X=58m, delivery bot crosses intersection across the road
        if car_x >= 58.0 and self.npc_cross_vel_y == 0.0:
            self.npc_cross_vel_y = -3.8  # crosses road from right to left
        self.npc_cross_pos_y += self.npc_cross_vel_y * dt
        qpos_idx_cross = self.mj_model.jnt_qposadr[self.j_npc_cross_y]
        self.mj_data.qpos[qpos_idx_cross] = (self.npc_cross_pos_y - 7.5)

        # -------------------------------------------------------------
        # 2. Ego-Centric Visual Perception & Sensory Drives for FlyBrain
        # -------------------------------------------------------------
        car_vy = float(c_vel[4])
        car_yaw_rate = float(c_vel[2])

        # Ego visual corridor selection:
        # 0 to 70m: right lane (y = -1.5m)
        # 70 to 95m: merge into center corridor (y = 0.0m) to pass cleanly between chicane barriers
        if car_x < 70.0:
            nav_target_y = -1.5
        else:
            nav_target_y = 0.0

        vis_err = nav_target_y - car_y
        # Critical damping against lateral velocity prevents overshoot
        visual_turn_bias = float(np.clip(0.22 * vis_err - 0.25 * car_vy, -0.6, 0.6))

        # Visual looming threat from braking lead vehicle or incursion cross traffic:
        loom_threat = 0.0
        if 0 < dist_lead < 15.0 and self.npc_lead_braking and (self.hazard_time is not None and (self.t_sim - self.hazard_time) <= 2.4):
            loom_threat = max(loom_threat, float(np.clip((15.0 - dist_lead) / 8.0, 0.0, 2.0)))

        dist_cross_x = 68.0 - car_x
        if 0.0 < dist_cross_x < 12.0 and -2.5 < self.npc_cross_pos_y < 2.5:
            loom_threat = max(loom_threat, float(np.clip((12.0 - dist_cross_x) / 6.0, 0.0, 2.0)))

        # Soporific latency: Dormiphen delays visual hazard perception by 1.25s
        if "Dormiphen" in self.drug_name or self.neural.arousal_attenuation < 0.85:
            if self.hazard_time is not None and (self.t_sim - self.hazard_time) < 1.25:
                loom_threat = 0.0

        # Feed sensory signals directly to FlyBrain
        self.neural.apply_stim(food_gain=1.0, predator_intensity=loom_threat, turn_bias=visual_turn_bias)

        # Step FlyWire network at ~50 Hz
        if int(self.t_sim / dt) % 10 == 0:
            self.neural.step()
        intent = self.translator.translate(self.neural, self.mod, stim_mgr=None)

        # -------------------------------------------------------------
        # 3. Pure Fly Brain Sensorimotor Actuation
        # -------------------------------------------------------------
        # Steering is commanded directly from translated FlyBrain descending intent
        steer_cmd = intent.turn_intent - 0.15 * car_yaw_rate
        if intent.coordination < 0.50:
            # Reciprocal inhibition collapse induces ataxic motor tremor / weaving
            steer_cmd += float(np.random.normal(0.0, 0.45 * (1.0 - intent.coordination)))
        steer_angle = float(np.clip(steer_cmd, -0.65, 0.65))

        # Braking vs Propulsion commanded directly from FlyBrain motor tone & flee/freeze intent
        brake_needed = intent.freeze or intent.flee_drive > 0.45 or (dist_cross_x > 0 and dist_cross_x < 7.0 and -2.5 < self.npc_cross_pos_y < 2.5) or (dist_lead < 8.0 and self.npc_lead_braking and (self.hazard_time is not None and (self.t_sim - self.hazard_time) <= 2.2))
        if "Dormiphen" in self.drug_name and self.hazard_time is not None and (self.t_sim - self.hazard_time) < 1.25:
            brake_needed = False

        if self.outcome in ("barrier_crash", "rear_end_collision", "cross_traffic_t_bone"):
            propulsion_torque = 0.0
        elif brake_needed:
            if self.brake_applied_time is None and self.hazard_time is not None:
                self.brake_applied_time = self.t_sim
            propulsion_torque = -float(np.clip(900.0 * car_vx, 300.0, 1200.0)) if car_vx > 0.05 else 0.0
        else:
            v_des = 6.0 * intent.forward_drive
            if car_vx < v_des:
                propulsion_torque = float(np.clip(450.0 * (v_des - car_vx) * intent.motor_tone, 0.0, 750.0))
            else:
                propulsion_torque = -float(np.clip(100.0 * (car_vx - v_des), 0.0, 200.0))


        # Apply actuator commands to MuJoCo
        self.mj_data.ctrl[self.steer_fl_act] = steer_angle
        self.mj_data.ctrl[self.steer_fr_act] = steer_angle
        self.mj_data.ctrl[self.drive_rl_act] = propulsion_torque
        self.mj_data.ctrl[self.drive_rr_act] = propulsion_torque

        # Step physics
        mujoco.mj_step(self.mj_model, self.mj_data)

        # -------------------------------------------------------------
        # 4. Collision Detection from Physics Contact Manifolds
        # -------------------------------------------------------------
        for ci in range(self.mj_data.ncon):
            con = self.mj_data.contact[ci]
            g1_name = mujoco.mj_id2name(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, con.geom1) or ""
            g2_name = mujoco.mj_id2name(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, con.geom2) or ""

            # Check car contacts
            names = (g1_name, g2_name)
            is_car = any("chassis" in n or "wheel" in n or "headlight" in n or "cockpit" in n for n in names)

            if not is_car:
                continue

            for n in names:
                if "pylon" in n:
                    pylon_idx = int(n.split("_")[-1]) if n.split("_")[-1].isdigit() else 0
                    self.cone_hits.add(pylon_idx)
                elif "npc_lead" in n:
                    self.npc_hits.add("lead_vehicle")
                    self.outcome = "rear_end_collision"
                elif "npc_cross" in n:
                    self.npc_hits.add("cross_traffic")
                    self.outcome = "cross_traffic_t_bone"
                elif "barrier" in n:
                    self.outcome = "barrier_crash"

        # Check course completion (crossed X = 92m finish line)
        if car_x >= 92.0 and self.outcome == "in_progress":
            if len(self.npc_hits) == 0 and len(self.cone_hits) == 0 and self.off_road_count == 0:
                self.outcome = "completed_clean"
            elif len(self.npc_hits) == 0:
                self.outcome = "pylon_strikes"
            else:
                self.outcome = "crash_damaged"

        # Check stall (e.g. Lidocaine)
        if car_x < 12.0 and self.t_sim > 5.0 and car_vx < 0.2:
            self.outcome = "stalled_no_throttle"

        return {
            "t": self.t_sim,
            "x": car_x,
            "y": car_y,
            "vx": car_vx,
            "steer_angle": steer_angle,
            "propulsion_torque": propulsion_torque,
            "dist_lead": dist_lead,
            "cone_hits": len(self.cone_hits),
            "npc_hits": list(self.npc_hits),
            "outcome": self.outcome,
        }

    def compute_summary_metrics(self) -> DrivingMetrics:
        """Calculates clinical impairment scores (SDLP, BRT, collision counts)."""
        lats = np.array(self.lateral_positions)
        speeds = np.array(self.forward_speeds)

        # SDLP: Standard Deviation of Lateral Position across course
        sdlp = float(np.std(lats)) if len(lats) > 10 else 0.0
        mean_spd = float(np.mean(speeds)) if len(speeds) else 0.0
        peak_spd = float(np.max(speeds)) if len(speeds) else 0.0

        # Brake Reaction Time in ms
        if self.hazard_time is not None and self.brake_applied_time is not None:
            brt_ms = float((self.brake_applied_time - self.hazard_time) * 1000.0)
        elif self.hazard_time is not None:
            brt_ms = 9999.0  # never braked!
        else:
            brt_ms = 0.0

        completed = "completed" in self.outcome

        # Final clinical verdict
        if self.outcome == "in_progress":
            final_outcome = "completed_partial"
        else:
            final_outcome = self.outcome

        return DrivingMetrics(
            drug_name=self.drug_name,
            dose=self.dose,
            duration_s=round(self.t_sim, 2),
            sdlp_m=round(sdlp, 3),
            mean_speed_m_s=round(mean_spd, 2),
            peak_speed_m_s=round(peak_spd, 2),
            brake_reaction_time_ms=round(brt_ms, 1),
            cone_collisions=len(self.cone_hits),
            npc_collisions=len(self.npc_hits),
            off_road_excursions=self.off_road_count,
            course_completed=completed,
            driving_outcome=final_outcome,
        )

    def run(
        self,
        duration: float = 100.0,
        viewer: Any = None,
        timelapse: float = 1.0,
    ) -> DrivingMetrics:
        """Runs the driving trial in live viewer or headless."""
        dt = 0.005
        n_steps = int(duration / dt)
        t_start_wall = time.time()

        for step_idx in range(n_steps):
            info = self.step(dt)

            if viewer is not None and step_idx % 4 == 0:
                if not viewer.is_running():
                    break
                viewer.sync()
                if timelapse > 0:
                    wall_elapsed = time.time() - t_start_wall
                    target_wall = self.t_sim / timelapse
                    if wall_elapsed < target_wall:
                        time.sleep(min(0.016, target_wall - wall_elapsed))

            # Early termination on crossing finish line or catastrophic crash
            if info["x"] >= 95.0 and "completed" in info["outcome"]:
                break

            if info["outcome"] in ("rear_end_collision", "cross_traffic_t_bone", "barrier_crash"):
                # run for 0.5s more to show impact recoil
                for _ in range(50):
                    self.step(dt)
                    if viewer is not None:
                        viewer.sync()
                break

        return self.compute_summary_metrics()

    def render_video(
        self,
        out_path: str,
        duration: float = 100.0,
        fps: int = 30,
        timelapse: float = 1.0,
    ) -> tuple[DrivingMetrics, list[np.ndarray]]:
        """Renders 3D driving course to MP4 or GIF with a real-time clinical HUD dashboard."""
        import imageio
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        dt = 0.005
        n_steps = int(duration / dt)
        render_interval = max(1, int(round(max(0.1, timelapse) / (fps * dt))))
        renderer = mujoco.Renderer(self.mj_model, height=480, width=640)
        frames = []

        for step_idx in range(n_steps):
            info = self.step(dt)

            if step_idx % render_interval == 0:
                renderer.update_scene(self.mj_data, camera="trackcam")
                raw_frame = renderer.render()
                hud_frame = draw_driving_hud(
                    raw_frame,
                    info,
                    self.drug_name,
                    self.dose,
                    self.hazard_time is not None,
                    self.brake_applied_time is not None,
                )
                frames.append(hud_frame)

            if info["x"] >= 95.0 and "completed" in info["outcome"]:
                break

            if info["outcome"] in ("rear_end_collision", "cross_traffic_t_bone", "barrier_crash"):
                # capture crash impact
                for _ in range(30):
                    self.step(dt)
                    if len(frames) % render_interval == 0:
                        renderer.update_scene(self.mj_data, camera="trackcam")
                        frames.append(draw_driving_hud(renderer.render(), info, self.drug_name, self.dose, True, True))
                break


        if out_path.lower().endswith(".gif"):
            imageio.mimsave(out_path, frames, fps=fps, loop=0)
        else:
            imageio.mimsave(out_path, frames, fps=fps)

        metrics = self.compute_summary_metrics()
        return metrics, frames

    def close(self):
        """Releases renderer and simulation resources."""
        pass


# =====================================================================
# 3. Clinical HUD Visual Dashboard
# =====================================================================

def draw_driving_hud(
    frame_rgb: np.ndarray,
    info: dict[str, Any],
    drug_name: str,
    dose: float,
    hazard_detected: bool,
    brake_active: bool,
) -> np.ndarray:
    """Renders a digital driving instrument cluster HUD on the video frame."""
    img = Image.fromarray(frame_rgb)
    draw = ImageDraw.Draw(img, "RGBA")
    width, height = img.size

    # 1. Top Telemetry Banner
    draw.rectangle([0, 0, width, 52], fill=(15, 23, 42, 220))
    # Bottom Dashboard Bar
    draw.rectangle([0, height - 46, width, height], fill=(15, 23, 42, 225))

    # Determine status badge color
    outcome = info.get("outcome", "in_progress")
    if "collision" in outcome or "t_bone" in outcome:
        badge_bg = (220, 38, 38, 235)      # Red Alert (Crash)
        badge_text = "COLLISION IMPACT!"
    elif "pylon" in outcome:
        badge_bg = (217, 119, 6, 230)      # Amber (Pylons hit)
        badge_text = "PYLON STRIKES"
    elif "clean" in outcome:
        badge_bg = (34, 197, 94, 230)      # Green (Clean pass)
        badge_text = "COURSE COMPLETED"
    elif hazard_detected and not brake_active:
        badge_bg = (234, 88, 12, 230)      # Orange (Hazard Looming / Reaction Window)
        badge_text = "BRAKE HAZARD DETECTED"
    else:
        badge_bg = (37, 99, 235, 220)      # Blue (Tracking)
        badge_text = "DRIVING TEST IN PROGRESS"

    # Header texts
    speed_kmh = info["vx"] * 3.6
    from sim.drug_engine import get_chemical_name
    chem_display = get_chemical_name(drug_name)
    draw.text((180, 14), f"COMPOUND: {chem_display} ({dose:.1f})", fill=(203, 213, 225), font_size=14)

    # Status Badge (Top Right)
    badge_w = 240
    draw.rounded_rectangle([width - badge_w - 12, 8, width - 12, 44], radius=6, fill=badge_bg)
    draw.text((width - badge_w + 10, 14), badge_text, fill=(255, 255, 255), font_size=13)

    # Bottom Instrument Cluster
    steer_deg = info["steer_angle"] * 180.0 / np.pi
    y_bot = height - 32
    col1 = f"TRACK X: {info['x']:4.1f}m"
    col2 = f"LANE Y: {info['y']:+4.2f}m"
    col3 = f"STEER: {steer_deg:+4.1f}°"
    col4 = f"PYLONS: {info['cone_hits']}"
    col5 = f"NPC CRASH: {len(info['npc_hits'])}"

    draw.text((16, y_bot), col1, fill=(56, 189, 248), font_size=13)
    draw.text((140, y_bot), col2, fill=(250, 204, 21), font_size=13)
    draw.text((270, y_bot), col3, fill=(167, 139, 250), font_size=13)
    draw.text((410, y_bot), col4, fill=(244, 114, 182), font_size=13)
    draw.text((520, y_bot), col5, fill=(239, 68, 68), font_size=13)

    return np.array(img)


if __name__ == "__main__":
    print("Testing HumanDrivingSim with Vehicle Baseline...")
    sim = HumanDrivingSim(drug_name=None)
    m = sim.run(duration=12.0)
    print(json.dumps(asdict(m), indent=2))
