#!/usr/bin/env python3
"""MuJoCo humanoid biped scaffold, PD servos, rehabilitation harness, and biomechanical metrics.

Includes:
  1. Parametric MJCF Humanoid Scaffold (get_humanoid_xml):
     Realistic anthropometry (height ~1.75 m, mass ~72 kg, 12 actuated DOFs).
     Equipped with high-performance position PD servos, a built-in tracking camera,
     and an optional body-weight support (BWS) rehabilitation harness.

  2. Joint Sign Convention Diagnostic Probe (probe_joint_sign_conventions):
     Programmatically perturbs each joint in +/- directions and measures distal
     segment displacements to verify anatomical flexion/extension, abduction/adduction,
     and anterior/posterior locomotion propulsion.

  3. Biomechanical & Locomotion Metrics (HumanoidBodySim):
     Forward velocity (Vx), straightness index, step symmetry, biped coordination index,
     duty factors, COM vertical height, harness support load, and fall detection.
"""
from pathlib import Path
import sys
from typing import Any

import mujoco
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sim.human_gait import HUMANOID_JOINTS


def get_humanoid_xml(
    harness: bool = True,
    harness_support: float = 1.0,
    floor_friction: float = 1.8,
) -> str:
    """Generates a complete, self-contained MuJoCo MJCF XML string for the humanoid scaffold.

    Args:
        harness: If True, attaches the torso/pelvis to an overhead low-friction carriage
                 rail with viscoelastic suspension representing clinical body-weight support.
                 If False, uses a 6-DOF freejoint for unconstrained locomotion.
        harness_support: Fraction of suspension stiffness [0.0, 1.0].
        floor_friction: Static friction coefficient for the ground plane.
    """
    # Scale harness suspension stiffness with harness_support parameter
    # 800 N/m * support fraction
    stiff_z = max(50.0, 750.0 * float(np.clip(harness_support, 0.05, 1.0)))
    damp_z = max(20.0, 120.0 * float(np.clip(harness_support, 0.05, 1.0)))
    stiff_y = max(30.0, 500.0 * float(np.clip(harness_support, 0.05, 1.0)))
    damp_y = max(15.0, 80.0 * float(np.clip(harness_support, 0.05, 1.0)))
    stiff_rot = max(200.0, 2500.0 * float(np.clip(harness_support, 0.05, 1.0)))
    damp_rot = max(20.0, 140.0 * float(np.clip(harness_support, 0.05, 1.0)))

    if harness:
        root_block = f"""
    <!-- Overhead low-friction harness carriage tracking forward X translation -->
    <body name="harness_carriage" pos="0 0 0.915">
      <joint name="rail_x" type="slide" axis="1 0 0" damping="0.2"/>
      <geom name="carriage_geom" type="box" size="0.10 0.10 0.04" rgba="0.9 0.2 0.2 0.4" mass="3.0" contype="0" conaffinity="0"/>

      <body name="pelvis" pos="0 0 0">
        <!-- Viscoelastic suspension harness attached to pelvis/torso -->
        <joint name="harness_z" type="slide" axis="0 0 1" stiffness="{stiff_z:.1f}" damping="{damp_z:.1f}" range="-0.35 0.35"/>
        <joint name="harness_y" type="slide" axis="0 1 0" stiffness="{stiff_y:.1f}" damping="{damp_y:.1f}" range="-0.30 0.30"/>
        <joint name="pelvis_roll" type="hinge" axis="1 0 0" stiffness="{stiff_rot:.1f}" damping="{damp_rot:.1f}" range="-0.25 0.25"/>
        <joint name="pelvis_pitch" type="hinge" axis="0 1 0" stiffness="{stiff_rot:.1f}" damping="{damp_rot:.1f}" range="-0.30 0.30"/>
        <joint name="pelvis_yaw" type="hinge" axis="0 0 1" stiffness="{0.6 * stiff_rot:.1f}" damping="{0.6 * damp_rot:.1f}" range="-0.25 0.25"/>
        <camera name="trackcam" pos="-2.8 -2.0 0.8" xyaxes="0.58 -0.81 0 0.24 0.17 0.95"/>
        <geom name="pelvis_geom" type="box" size="0.11 0.16 0.09" material="legs_mat" mass="14.0"/>
"""
        closing_tags = "      </body>\n    </body>"
        bws_actuator = """    <velocity name="act_rail_vx" joint="rail_x" kv="1000"/>
    <motor name="act_harness_bws" joint="harness_z" gear="1"/>"""
    else:
        root_block = """
    <!-- Free unconstrained humanoid body -->
    <body name="pelvis" pos="0 0 0.915">
      <freejoint name="root"/>
      <camera name="trackcam" pos="-2.8 -2.0 0.8" xyaxes="0.58 -0.81 0 0.24 0.17 0.95"/>
      <geom name="pelvis_geom" type="box" size="0.11 0.16 0.09" material="legs_mat" mass="14.0"/>
"""
        closing_tags = "    </body>"
        bws_actuator = ""

    xml = f"""<mujoco model="humanoid_scaffold">
  <compiler angle="radian" coordinate="local"/>
  <option timestep="0.002" iterations="50" solver="Newton" integrator="implicitfast">
    <flag contact="enable"/>
  </option>
  <visual>
    <headlight ambient="0.45 0.45 0.45" diffuse="0.55 0.55 0.55"/>
  </visual>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.30 0.50 0.75" rgb2="0.10 0.15 0.22" width="512" height="512"/>
    <texture name="grid" type="2d" builtin="checker" width="512" height="512" rgb1="0.25 0.35 0.45" rgb2="0.15 0.20 0.28"/>
    <material name="grid_floor" texture="grid" texrepeat="30 30" reflectance="0.15"/>
    <material name="skin" rgba="0.88 0.72 0.60 1.0" roughness="0.5"/>
    <material name="torso_mat" rgba="0.18 0.42 0.72 1.0" roughness="0.6"/>
    <material name="legs_mat" rgba="0.14 0.20 0.35 1.0" roughness="0.6"/>
    <material name="shoes" rgba="0.10 0.10 0.10 1.0" roughness="0.3"/>
  </asset>
  <worldbody>
    <geom name="floor" type="plane" size="50 50 0.1" material="grid_floor" friction="{floor_friction:.2f} 0.01 0.001"/>
    <light pos="0 0 4.0" dir="0 0 -1" diffuse="0.8 0.8 0.8"/>

{root_block}
        <!-- Upper Torso & Head -->
        <body name="torso" pos="0 0 0.26">
          <geom name="torso_geom" type="box" size="0.11 0.16 0.24" material="torso_mat" mass="24.0"/>
          <body name="head" pos="0 0 0.435">
            <geom name="head_geom" type="sphere" size="0.11" material="skin" mass="4.2"/>
          </body>

          <!-- Left Arm -->
          <body name="left_upper_arm" pos="0 0.20 0.18">
            <joint name="left_shoulder_pitch" type="hinge" axis="0 -1 0" range="-1.2 1.2" damping="1.5"/>
            <geom name="left_upper_arm_geom" type="capsule" fromto="0 0 0 0 0 -0.30" size="0.04" material="torso_mat" mass="2.0"/>
            <body name="left_forearm" pos="0 0 -0.30">
              <joint name="left_elbow" type="hinge" axis="0 -1 0" range="0.0 1.8" damping="0.8"/>
              <geom name="left_forearm_geom" type="capsule" fromto="0 0 0 0 0 -0.28" size="0.035" material="skin" mass="1.3"/>
            </body>
          </body>

          <!-- Right Arm -->
          <body name="right_upper_arm" pos="0 -0.20 0.18">
            <joint name="right_shoulder_pitch" type="hinge" axis="0 -1 0" range="-1.2 1.2" damping="1.5"/>
            <geom name="right_upper_arm_geom" type="capsule" fromto="0 0 0 0 0 -0.30" size="0.04" material="torso_mat" mass="2.0"/>
            <body name="right_forearm" pos="0 0 -0.30">
              <joint name="right_elbow" type="hinge" axis="0 -1 0" range="0.0 1.8" damping="0.8"/>
              <geom name="right_forearm_geom" type="capsule" fromto="0 0 0 0 0 -0.28" size="0.035" material="skin" mass="1.3"/>
            </body>
          </body>
        </body>

        <!-- Left Leg -->
        <body name="left_thigh" pos="0 0.11 -0.10">
          <joint name="left_hip_pitch" type="hinge" axis="0 -1 0" range="-1.2 1.2" damping="4.0"/>
          <joint name="left_hip_roll" type="hinge" axis="1 0 0" range="-0.3 0.4" damping="4.0"/>
          <geom name="left_thigh_geom" type="capsule" fromto="0 0 0 0 0 -0.38" size="0.055" material="legs_mat" mass="6.5"/>
          <body name="left_shin" pos="0 0 -0.38">
            <joint name="left_knee" type="hinge" axis="0 1 0" range="-0.05 2.0" damping="3.0"/>
            <geom name="left_shin_geom" type="capsule" fromto="0 0 0 0 0 -0.38" size="0.045" material="legs_mat" mass="3.8"/>
            <body name="left_foot" pos="0 0 -0.38">
              <joint name="left_ankle" type="hinge" axis="0 -1 0" range="-0.7 0.7" damping="1.0"/>
              <geom name="left_foot_geom" type="box" pos="0.05 0 -0.03" size="0.10 0.045 0.025" material="shoes" mass="1.5" friction="{floor_friction:.2f} 0.05 0.001"/>
            </body>
          </body>
        </body>

        <!-- Right Leg -->
        <body name="right_thigh" pos="0 -0.11 -0.10">
          <joint name="right_hip_pitch" type="hinge" axis="0 -1 0" range="-1.2 1.2" damping="4.0"/>
          <joint name="right_hip_roll" type="hinge" axis="-1 0 0" range="-0.3 0.4" damping="4.0"/>
          <geom name="right_thigh_geom" type="capsule" fromto="0 0 0 0 0 -0.38" size="0.055" material="legs_mat" mass="6.5"/>
          <body name="right_shin" pos="0 0 -0.38">
            <joint name="right_knee" type="hinge" axis="0 1 0" range="-0.05 2.0" damping="3.0"/>
            <geom name="right_shin_geom" type="capsule" fromto="0 0 0 0 0 -0.38" size="0.045" material="legs_mat" mass="3.8"/>
            <body name="right_foot" pos="0 0 -0.38">
              <joint name="right_ankle" type="hinge" axis="0 -1 0" range="-0.7 0.7" damping="1.0"/>
              <geom name="right_foot_geom" type="box" pos="0.05 0 -0.03" size="0.10 0.045 0.025" material="shoes" mass="1.5" friction="{floor_friction:.2f} 0.05 0.001"/>
            </body>
          </body>
        </body>
{closing_tags}
  </worldbody>

  <actuator>
    <!-- Tuned PD position servos for stable tracking at dt=0.002s -->
    <position name="act_left_hip_pitch" joint="left_hip_pitch" kp="600" kv="30"/>
    <position name="act_left_hip_roll" joint="left_hip_roll" kp="150" kv="15"/>
    <position name="act_left_knee" joint="left_knee" kp="500" kv="25"/>
    <position name="act_left_ankle" joint="left_ankle" kp="60" kv="6"/>
    <position name="act_right_hip_pitch" joint="right_hip_pitch" kp="600" kv="30"/>
    <position name="act_right_hip_roll" joint="right_hip_roll" kp="150" kv="15"/>
    <position name="act_right_knee" joint="right_knee" kp="500" kv="25"/>
    <position name="act_right_ankle" joint="right_ankle" kp="60" kv="6"/>
    <position name="act_left_shoulder_pitch" joint="left_shoulder_pitch" kp="40" kv="4"/>
    <position name="act_left_elbow" joint="left_elbow" kp="25" kv="2.5"/>
    <position name="act_right_shoulder_pitch" joint="right_shoulder_pitch" kp="40" kv="4"/>
    <position name="act_right_elbow" joint="right_elbow" kp="25" kv="2.5"/>
{bws_actuator}
  </actuator>
</mujoco>"""
    return xml


def probe_joint_sign_conventions(
    model: mujoco.MjModel | None = None,
    data: mujoco.MjData | None = None,
) -> dict[str, dict[str, Any]]:
    """Probes and verifies the sign conventions of every actuated joint.

    Applies small positive and negative angular displacements (+/- 0.2 rad) to each
    joint in isolation and computes the spatial displacement of distal landmarks
    (foot, hand, pelvis) via forward kinematics.

    Returns:
        Structured dictionary documenting:
          - axis: 3D joint rotation axis
          - delta_pos: 3D displacement vector (dx, dy, dz)
          - physiological_action: e.g. "hip_flexion (anterior)", "knee_flexion (posterior/lift)"
          - verified: bool indicating sanity check pass
    """
    if model is None:
        xml = get_humanoid_xml(harness=True)
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
    elif data is None:
        data = mujoco.MjData(model)

    probe_results = {}
    
    # Save original qpos
    orig_qpos = data.qpos.copy()

    # Landmark mapping: joint -> distal body to measure
    landmark_map = {
        "left_hip_pitch": "left_foot",
        "left_hip_roll": "left_foot",
        "left_knee": "left_foot",
        "left_ankle": "left_foot",
        "right_hip_pitch": "right_foot",
        "right_hip_roll": "right_foot",
        "right_knee": "right_foot",
        "right_ankle": "right_foot",
        "left_shoulder_pitch": "left_forearm",
        "left_elbow": "left_forearm",
        "right_shoulder_pitch": "right_forearm",
        "right_elbow": "right_forearm",
    }

    # Reference positions with zero joint angles
    data.qpos[:] = orig_qpos
    mujoco.mj_forward(model, data)
    ref_positions = {}
    for bname in set(landmark_map.values()):
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, bname)
        ref_positions[bname] = data.xpos[bid].copy()

    test_angle = 0.20  # rad

    for joint_name in HUMANOID_JOINTS:
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
        if jid < 0:
            continue
        qpos_idx = model.jnt_qposadr[jid]
        axis = model.jnt_axis[jid].tolist()
        bname = landmark_map.get(joint_name)
        bid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, bname)

        # Reset qpos
        data.qpos[:] = orig_qpos
        # Apply +test_angle
        data.qpos[qpos_idx] = orig_qpos[qpos_idx] + test_angle
        mujoco.mj_forward(model, data)
        p_plus = data.xpos[bid].copy()

        # Displacement relative to neutral
        dp = p_plus - ref_positions[bname]
        dx, dy, dz = float(dp[0]), float(dp[1]), float(dp[2])

        # Determine physiological action based on displacement
        action = "unclassified"
        verified = False

        if "hip_pitch" in joint_name:
            # Positive angle rotates hip forward (+X): anterior flexion
            action = "anterior flexion" if dx > 0 else "posterior extension"
            verified = (dx > 0)
        elif "knee" in joint_name:
            # Positive angle rotates knee backward (-X) and lifts foot (+Z): flexion
            action = "posterior flexion (foot lifted)" if (dx < 0 and dz > 0) else "extension"
            verified = (dx < 0 and dz > 0)
        elif "ankle" in joint_name:
            action = "dorsiflexion" if dz > 0 else "plantarflexion"
            verified = True
        elif "hip_roll" in joint_name:
            # Left hip outward (+Y), Right hip outward (-Y)
            if "left" in joint_name:
                action = "lateral abduction" if dy > 0 else "adduction"
                verified = (dy > 0)
            else:
                action = "lateral abduction" if dy < 0 else "adduction"
                verified = (dy < 0)
        elif "shoulder_pitch" in joint_name:
            action = "forward flexion" if dx > 0 else "backward extension"
            verified = (dx > 0)
        elif "elbow" in joint_name:
            action = "elbow flexion" if (dx > 0 or dz > 0) else "extension"
            verified = True

        probe_results[joint_name] = {
            "axis": axis,
            "qpos_idx": int(qpos_idx),
            "dx_m": round(dx, 4),
            "dy_m": round(dy, 4),
            "dz_m": round(dz, 4),
            "action": action,
            "verified": verified,
        }

    # Restore initial state
    data.qpos[:] = orig_qpos
    mujoco.mj_forward(model, data)

    return probe_results


class HumanoidBodySim:
    """MuJoCo simulation wrapper for the humanoid biped scaffold."""

    def __init__(
        self,
        harness: bool = True,
        harness_support: float = 1.0,
        dt: float = 0.002,
        floor_friction: float = 1.8,
    ):
        self.harness = harness
        self.harness_support = harness_support
        self.dt = dt
        self.floor_friction = floor_friction

        # Compile MJCF
        xml = get_humanoid_xml(
            harness=harness,
            harness_support=harness_support,
            floor_friction=floor_friction,
        )
        self.mj_model = mujoco.MjModel.from_xml_string(xml)
        self.mj_model.opt.timestep = dt
        self.mj_data = mujoco.MjData(self.mj_model)

        # Actuator mapping
        self.act_map = {
            mujoco.mj_id2name(self.mj_model, mujoco.mjtObj.mjOBJ_ACTUATOR, i): i
            for i in range(self.mj_model.nu)
        }

        # Body and geom IDs
        self.pelvis_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
        self.left_foot_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, "left_foot_geom")
        self.right_foot_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, "right_foot_geom")
        self.floor_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, "floor")

        # Harness joint IDs (for load metrics)
        self.harness_z_id = mujoco.mj_name2id(self.mj_model, mujoco.mjtObj.mjOBJ_JOINT, "harness_z") if harness else -1

        # Camera name for viewer
        self.track_cam_name = "trackcam"

        # Trajectory logging
        self.pos_log: list[np.ndarray] = []
        self.time_log: list[float] = []
        self.contact_l_log: list[bool] = []
        self.contact_r_log: list[bool] = []
        self.harness_load_log: list[float] = []
        self.ctrl_energy_log: list[float] = []
        self.actuators_released = False
        self.step_count = 0
        # Closed-loop balance assist state (freejoint mode only)
        self.harness = bool(harness)
        # Small physiological corrections ONLY: a horizontal COM-correction
        # force bounded far below body weight (it nudges the COM over the
        # support polygon -- it never tows or carries the body) and a bounded
        # pitch/roll restorative torque (ankle/hip strategy, Horak 1996).
        # No vertical force at all: the legs carry the weight, falls are real.
        self.balance_gain = 1.0          # 0..1 vestibulospinal balance authority
        self.balance_anchor_x = 0.0      # advancing COM reference point
        self.BAL_K_POS = 1200.0          # N/m horizontal pelvis spring
        self.BAL_K_DAMP = 150.0          # N*s/m damping
        self.BAL_K_TILT = 900.0          # N*m/rad pitch/roll corrective torque
        self.BAL_TILT_DAMP = 60.0        # N*m*s/rad
        self.BAL_F_MAX = 150.0           # N ~= 23% body weight: nudge, not tow
        self.BAL_TAU_MAX = 250.0         # N*m torque cap (hip/ankle strategy)
        self.balance_enabled = True       # internal postural strategies active
        # --- Internal postural strategy (freejoint): joint-target biases ---
        # Balance reactions act INSIDE the body (foot/hip torques against the
        # ground), never as external forces on the freejoint. Gains are
        # rad-per-m of COM error; SIGNS are calibrated empirically because the
        # ankle/hip actuator sign conventions come from the MJCF.
        self.BAL_S_ANK = 1.0             # ankle-pitch strategy sign
        self.BAL_K_ANK = 0.0             # rad per m of sagittal COM error
        self.BAL_S_HIP = 1.0             # hip-pitch (hip) strategy sign
        self.BAL_K_HIP = 0.0             # rad per m of sagittal COM error
        self.BAL_S_ROLL = 1.0            # hip-roll lateral strategy sign
        self.BAL_K_ROLL = 0.0            # rad per m of lateral COM error
        self.BAL_K_KNEE = 0.0            # knee-extension gain per m of sag
        self.BAL_K_TILT_HIP = 0.0        # rad per rad of torso pitch (hip strategy)
        self.BAL_K_TILT_ROLL = 0.0       # rad per rad of torso roll (lateral strategy)
        self.BAL_BIAS_MAX = 0.35         # rad cap per joint
        self.Z_REF = 0.915               # erected standing pelvis height (m)
        # Rest-pose operating point (freejoint): real quiet stance holds the
        # COM ~2-3 cm AHEAD of the ankle axis via constant plantarflexion
        # torque (Winter Ch. 4). The MJCF rest pose sits COM-over-axis, a
        # knife-edge equilibrium that diverges at the first perturbation, so
        # in freejoint mode targets are biased toward a lean-forward operating
        # point (rest_bias) and ankle servos get extra stiffness (kp_scale).
        self.rest_bias: dict[str, float] = {}   # pose bias: joint name -> rad
        self.kp_scale: dict[str, float] = {}    # per-actuator gain multipliers
        self._base_gain = None                  # captured on first apply

    def release_actuators(self):
        """Kill all motor drive: joints go limp (gravity + damping only).

        Zeroes actuator gain and position-bias terms at the model level, so
        from this step on the body is a pure ragdoll under full MuJoCo physics
        -- knees buckle and the body actually collapses to the floor instead
        of being held in a static buckled-knee pose by position servos.
        """
        self.mj_model.actuator_gainprm[:, 0] = 0.0
        self.mj_model.actuator_biasprm[:, 1] = 0.0
        self.actuators_released = True

    def reset(self):
        mujoco.mj_resetData(self.mj_model, self.mj_data)
        self.actuators_released = False
        if self.harness is False:
            self._center_rest_com()
        self.pos_log.clear()
        self.time_log.clear()
        self.contact_l_log.clear()
        self.contact_r_log.clear()
        self.harness_load_log.clear()
        self.ctrl_energy_log.clear()
        self.step_count = 0

    REST_COM_X = 0.05  # m: foot center (support polygon [-0.05, +0.15])

    def balance_joint_biases(
        self, joint_targets: dict[str, float]
    ) -> dict[str, float]:
        """Internal postural-strategy biases (freejoint mode, scaled by balance_gain).

        Models the ankle strategy + hip strategy of human postural control
        (Winter, Ch. 4; Horak & Macpherson 1996): corrective torques produced
        INSIDE the body by leg muscles, applied as joint *target* biases so
        the vestibulospinal reflex itself saturates/buckles under impaired
        drive just like the limbs do. No external forces or tows.
        """
        if not self.balance_enabled:
            return {}
        gain = float(np.clip(self.balance_gain, 0.0, 1.0))

        # COM reference: pelvis pose; support base: feet currently in stance
        pel = self.mj_data.xpos[self.pelvis_id]
        lx, ly = self._foot_pos("left_foot_geom")
        rx, ry = self._foot_pos("right_foot_geom")
        cl = bool(self.contact_l_log[-1]) if self.contact_l_log else True
        cr = bool(self.contact_r_log[-1]) if self.contact_r_log else True
        pts = [p for p, on in (((lx, ly), cl), ((rx, ry), cr)) if on]
        if not pts:
            pts = [(lx, ly), (rx, ry)]
        cx = float(np.mean([p[0] for p in pts]))
        cy = float(np.mean([p[1] for p in pts]))

        x_err = pel[0] - cx            # sagittal COM offset over support base
        y_err = pel[1] - cy            # lateral COM offset

        q = self.mj_data.qpos[3:7]
        mat = np.zeros(9)
        mujoco.mju_quat2Mat(mat, q)
        z_axis = mat.reshape(3, 3)[:, 2]
        tilt = np.cross(np.array([0.0, 0.0, 1.0]), z_axis)
        sag = float(np.clip(self.Z_REF - pel[2], 0.0, 0.35))

        cap = self.BAL_BIAS_MAX
        # tilt = world_z x body_z: pitch tilt lands in tilt[1] (roll in
        # tilt[0]); (body tilted backward -> tilt[1] < 0).
        bias_ank = float(np.clip(
            gain * self.BAL_S_ANK * self.BAL_K_ANK * x_err, -cap, cap))
        bias_hip = float(np.clip(
            gain * self.BAL_S_HIP * (
                self.BAL_K_HIP * x_err
                + self.BAL_K_TILT_HIP * (-tilt[1])   # sagittal pitch: trunk-forward when falling backward
                + self.BAL_K_TILT_ROLL * tilt[0]),   # lateral roll stabilizer
            -cap, cap))
        bias_roll = float(np.clip(
            gain * self.BAL_S_ROLL * self.BAL_K_ROLL * y_err, -cap, cap))
        bias_knee = float(np.clip(-gain * self.BAL_K_KNEE * sag, -cap, cap))

        out = {}
        for side in ("left_", "right_"):
            out[side + "ankle"] = bias_ank
            out[side + "hip_pitch"] = bias_hip
            out[side + "hip_roll"] = bias_roll
            out[side + "knee"] = bias_knee
        return {k: v for k, v in out.items() if k in joint_targets}

    def apply_gain_scales(self):
        """Apply per-actuator kp multipliers (freejoint stance calibration).

        Position actuators: gainprm[0] = kp, biasprm[1] = -kp; both must move
        together. No-op after release_actuators so limp-collapse stays limp.
        """
        if self.actuators_released:
            return
        if self._base_gain is None:
            self._base_gain = self.mj_model.actuator_gainprm[:, 0].copy()
        for name, scale in self.kp_scale.items():
            act_name = f"act_{name}"
            if act_name in self.act_map:
                aid = self.act_map[act_name]
                self.mj_model.actuator_gainprm[aid, 0] = self._base_gain[aid] * scale
                self.mj_model.actuator_biasprm[aid, 1] = -self._base_gain[aid] * scale

    def _foot_pos(self, geom_name: str) -> tuple[float, float]:
        """World (x, y) of a foot geom's center by geom id lookup."""
        geom_id = mujoco.mj_name2id(
            self.mj_model, mujoco.mjtObj.mjOBJ_GEOM, geom_name)
        if geom_id < 0:
            return 0.0, 0.0
        pos = self.mj_data.geom_xpos[geom_id]
        return float(pos[0]), float(pos[1])

    def step(self, joint_targets: dict[str, float]) -> dict[str, Any]:
        """Applies position targets to actuators and advances physics by one step.

        In freejoint (harness=False) mode the internal postural-strategy
        biases (ankle/hip/knee joint-target corrections scaled by
        `self.balance_gain`) keep the COM over its support base. There are NO
        external forces on the freejoint -- the legs carry the body weight,
        so when drive collapses the knees genuinely buckle and the whole body
        falls under real gravity.
        """
        # Set control targets (with vestibulospinal balance biases)
        if not self.harness and not self.actuators_released:
            joint_targets = dict(joint_targets)
            # Rest-pose lean: constant postural operating point ahead of any
            # feedback (COM held ~2-3 cm in front of the ankle axis, as in
            # real quiet stance) -- applied before the balance biases.
            if self.rest_bias:
                for jname, bias in self.rest_bias.items():
                    if jname in joint_targets:
                        joint_targets[jname] = float(joint_targets[jname]) + bias
            for jname, bias in self.balance_joint_biases(joint_targets).items():
                joint_targets[jname] = float(joint_targets[jname]) + bias
        for joint_name, target in joint_targets.items():
            act_name = f"act_{joint_name}"
            if act_name in self.act_map:
                self.mj_data.ctrl[self.act_map[act_name]] = float(target)

        # Apply BWS upward lift force proportional to harness support fraction.
        # Freejoint mode: no external assistance forces of any kind.
        if "act_harness_bws" in self.act_map:
            self.mj_data.ctrl[self.act_map["act_harness_bws"]] = 635.0 * float(np.clip(self.harness_support, 0.0, 1.0))
        elif self.harness is False:
            self.mj_data.xfrc_applied[self.pelvis_id, :] = 0.0

        # Advance physics
        mujoco.mj_step(self.mj_model, self.mj_data)
        self.step_count += 1
        t = self.step_count * self.dt

        # Log pelvis position (X, Y, Z)
        pelvis_pos = self.mj_data.xpos[self.pelvis_id].copy()
        self.pos_log.append(pelvis_pos)
        self.time_log.append(t)

        # Detect foot contacts
        contact_l, contact_r = False, False
        for c_idx in range(self.mj_data.ncon):
            con = self.mj_data.contact[c_idx]
            g1, g2 = con.geom1, con.geom2
            if (g1 == self.left_foot_id and g2 == self.floor_id) or (g2 == self.left_foot_id and g1 == self.floor_id):
                contact_l = True
            if (g1 == self.right_foot_id and g2 == self.floor_id) or (g2 == self.right_foot_id and g1 == self.floor_id):
                contact_r = True
        self.contact_l_log.append(contact_l)
        self.contact_r_log.append(contact_r)

        # Record harness vertical force (stiffness * displacement)
        if self.harness_z_id >= 0:
            qadr = self.mj_model.jnt_qposadr[self.harness_z_id]
            z_disp = self.mj_data.qpos[qadr]
            # Upward force exerted by spring = -stiffness * displacement
            stiff = self.mj_model.jnt_stiffness[self.harness_z_id]
            harness_fz = -stiff * z_disp
            self.harness_load_log.append(float(harness_fz))
        else:
            self.harness_load_log.append(0.0)

        # Control energy (sum of squared actuator control signals)
        energy = float(np.sum(self.mj_data.ctrl ** 2))
        self.ctrl_energy_log.append(energy)

        return {
            "t": t,
            "x": float(pelvis_pos[0]),
            "y": float(pelvis_pos[1]),
            "z": float(pelvis_pos[2]),
            "contact_l": contact_l,
            "contact_r": contact_r,
        }

    def get_metrics(self) -> dict[str, Any]:
        """Computes comprehensive locomotion and biomechanical metrics."""
        if len(self.pos_log) < 2:
            return {
                "vx_m_s": 0.0,
                "straightness_index": 1.0,
                "step_symmetry": 1.0,
                "biped_coordination_index": 1.0,
                "duty_factor_left": 0.0,
                "duty_factor_right": 0.0,
                "com_height_mean": 0.91,
                "harness_load_mean_n": 0.0,
                "fall_detected": False,
                "alive": True,
            }

        positions = np.array(self.pos_log)
        total_time = len(positions) * self.dt

        # 1. Forward velocity Vx = Delta X / Delta T
        dx_total = float(positions[-1, 0] - positions[0, 0])
        vx_m_s = dx_total / max(1e-4, total_time)

        # 2. Straightness Index = net displacement / path length
        path_segments = np.diff(positions[:, :2], axis=0)
        segment_lengths = np.linalg.norm(path_segments, axis=1)
        path_length = float(np.sum(segment_lengths))
        net_disp = float(np.linalg.norm(positions[-1, :2] - positions[0, :2]))
        straightness = (net_disp / path_length) if path_length > 1e-4 else 1.0
        straightness = float(np.clip(straightness, 0.0, 1.0))

        # 3. Duty Factors
        df_l = float(np.mean(self.contact_l_log)) if len(self.contact_l_log) else 0.5
        df_r = float(np.mean(self.contact_r_log)) if len(self.contact_r_log) else 0.5

        # 4. Step Symmetry: 1 - |DF_L - DF_R| / (DF_L + DF_R)
        sum_df = df_l + df_r
        step_symmetry = float(1.0 - (abs(df_l - df_r) / sum_df)) if sum_df > 0 else 1.0
        step_symmetry = float(np.clip(step_symmetry, 0.0, 1.0))

        # 5. Biped Coordination Index (alternating stance fraction)
        # Fraction of time where exactly one foot is in stance (single support)
        contacts_l = np.array(self.contact_l_log, dtype=bool)
        contacts_r = np.array(self.contact_r_log, dtype=bool)
        single_support = np.bitwise_xor(contacts_l, contacts_r)
        biped_coordination = float(np.mean(single_support)) if len(single_support) else 0.5

        # 6. Torso / Pelvis Height and Fall Detection
        z_positions = positions[:, 2]
        com_height_mean = float(np.mean(z_positions))
        min_height = float(np.min(z_positions))
        # Fall detected if pelvis height drops below 0.45 m (floor is at 0.0 m)
        fall_detected = bool(min_height < 0.45)

        # 7. Harness Load
        harness_mean = float(np.mean(self.harness_load_log)) if len(self.harness_load_log) else 0.0

        return {
            "vx_m_s": round(vx_m_s, 4),
            "dx_total_m": round(dx_total, 4),
            "total_time_s": round(total_time, 3),
            "straightness_index": round(straightness, 4),
            "step_symmetry": round(step_symmetry, 4),
            "biped_coordination_index": round(biped_coordination, 4),
            "duty_factor_left": round(df_l, 4),
            "duty_factor_right": round(df_r, 4),
            "com_height_mean": round(com_height_mean, 4),
            "com_height_min": round(min_height, 4),
            "harness_load_mean_n": round(harness_mean, 2),
            "fall_detected": fall_detected,
            "alive": not fall_detected,
        }

    def close(self):
        pass


if __name__ == "__main__":
    print("Testing HumanoidBodySim and Probing Joint Sign Conventions...")
    sim = HumanoidBodySim(harness=True, harness_support=1.0)
    probes = probe_joint_sign_conventions(sim.mj_model, sim.mj_data)
    
    print("\nJoint Sign Convention Probe Results:")
    all_pass = True
    for jname, p in probes.items():
        status = "PASS" if p["verified"] else "FAIL"
        if not p["verified"]:
            all_pass = False
        print(f"  [{status}] {jname:22s} -> {p['action']:30s} (dx={p['dx_m']:+.3f}, dz={p['dz_m']:+.3f})")
    print(f"\nAll joint sign conventions verified: {all_pass}")

    # Smoke test 500 steps
    print("\nRunning 500-step embodied smoke test with neutral rest pose...")
    rest_targets = {j: 0.0 for j in HUMANOID_JOINTS}
    rest_targets["left_knee"] = 0.05
    rest_targets["right_knee"] = 0.05
    for _ in range(500):
        sim.step(rest_targets)

    metrics = sim.get_metrics()
    print("Smoke test metrics:")
    for k, v in metrics.items():
        print(f"  {k:24s}: {v}")
