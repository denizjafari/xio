import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# For 3D axes
from mpl_toolkits.mplot3d import Axes3D
from scipy.spatial.transform import Rotation as R
from matplotlib.animation import FuncAnimation

##############################################################################
# 1) LOAD AND ORGANIZE DATA
##############################################################################

folder_path = r"/home/jafarid/code/xio/DataLogger/21Feb-IMU"

files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

imu_data = {}
for file in files:
    parts = file.split("_")
    imu_id = parts[0]  # e.g., "IMU-1", "IMU-2", etc.

    if "quaternion" in file:
        data_type = "quaternion_log"
    else:
        continue

    file_path = os.path.join(folder_path, file)
    df = pd.read_csv(file_path)

    if "timestamp" not in df.columns:
        if "Time" in df.columns:
            df.rename(columns={"Time": "timestamp"}, inplace=True)
        else:
            print(f"'timestamp' column missing in {imu_id}. Found columns: {df.columns.tolist()}")
            continue

    if imu_id not in imu_data:
        imu_data[imu_id] = {}
    imu_data[imu_id][data_type] = df

processed_data = {}
for imu_id, data_dict in imu_data.items():
    if "quaternion_log" in data_dict:
        motion_data = data_dict["quaternion_log"].sort_values("timestamp")
        processed_data[imu_id] = motion_data

if not processed_data:
    print("No valid data processed. Please check input files.")
    exit()

##############################################################################
# 2) DEFINE THE SKELETON HIERARCHY
##############################################################################

ROOT_ID = "ROOT"

imu_hierarchy = {
    "IMU-6": (ROOT_ID, 0.1),
    "IMU-5": ("IMU-6", 0.3),
    "IMU-4": ("IMU-5", 0.15),
    "IMU-3": ("IMU-4", 0.18),
    "IMU-2": ("IMU-3", 0.15),
    "IMU-1": ("IMU-2", 0.09),
}

unit_vectors = {
    "IMU-6": np.array([-1,  0,  0]),
    "IMU-5": np.array([-1,  0,  0]),
    "IMU-4": np.array([ 1,  0,  0]),
    "IMU-3": np.array([ 1,  0,  0]),
    "IMU-2": np.array([ 1,  0,  0]),
    "IMU-1": np.array([ 1,  0,  0]),
}

segment_positions = {ROOT_ID: np.array([0, 0, 0])}

num_frames = min(len(df) for df in processed_data.values())
if num_frames == 0:
    print("No valid frames to animate.")
    exit()

##############################################################################
# 3) PREPARE FIGURE: 3D SKELETON (LEFT) + JOINT ANGLES (RIGHT)
##############################################################################

fig = plt.figure(figsize=(12, 6))

ax3d = fig.add_subplot(121, projection='3d')
ax3d.set_title("Wireframe Skeleton Animation")
ax3d.set_xlabel("X-axis")
ax3d.set_ylabel("Y-axis")
ax3d.set_zlabel("Z-axis")

axAng = fig.add_subplot(122)
axAng.set_xlim(0, num_frames)
axAng.set_ylim(0, 180)
axAng.set_xlabel("Frame")
axAng.set_ylabel("Angle (degrees)")
axAng.set_title("Shoulder & Elbow Angles (Absolute)")

lines = {}
imu_colors = {
    "IMU-1": "red",
    "IMU-2": "blue",
    "IMU-3": "green",
    "IMU-4": "purple",
    "IMU-5": "orange",
    "IMU-6": "black",
}
imu_labels = {
    "IMU-1": "Hand",
    "IMU-2": "Forearm",
    "IMU-3": "Upper Arm",
    "IMU-4": "Shoulder",
    "IMU-5": "Chest-Back",
    "IMU-6": "Torso",
}

for child_id, (parent_id, _) in imu_hierarchy.items():
    color = imu_colors.get(child_id, "gray")
    label = imu_labels.get(child_id, child_id)
    line, = ax3d.plot([], [], [], 'o-', color=color, label=label)
    lines[child_id] = line

ax3d.legend(loc='upper right', fontsize=9, frameon=True)

shoulder_angles = np.zeros(num_frames)
elbow_angles = np.zeros(num_frames)

angle_line_shoulder, = axAng.plot([], [], 'g-', label='Shoulder Angle')
angle_line_elbow,   = axAng.plot([], [], 'b-', label='Elbow Angle')
axAng.legend()

##############################################################################
# 4) MAKE AXES EQUAL IN 3D
##############################################################################

def set_axes_equal(ax):
    """
    Ensures equal aspect ratio in 3D, so the skeleton doesn't look distorted.
    """
    x_limits = ax.get_xlim3d()
    y_limits = ax.get_ylim3d()
    z_limits = ax.get_zlim3d()

    x_range = abs(x_limits[1] - x_limits[0])
    y_range = abs(y_limits[1] - y_limits[0])
    z_range = abs(z_limits[1] - z_limits[0])
    max_range = max(x_range, y_range, z_range)

    mid_x = np.mean(x_limits)
    mid_y = np.mean(y_limits)
    mid_z = np.mean(z_limits)

    ax.set_xlim3d([mid_x - max_range/2, mid_x + max_range/2])
    ax.set_ylim3d([mid_y - max_range/2, mid_y + max_range/2])
    ax.set_zlim3d([mid_z - max_range/2, mid_z + max_range/2])

##############################################################################
# 5) ANGLE BETWEEN TWO VECTORS (IN 3D)
##############################################################################

def angle_between(v1, v2):
    """
    Returns the angle in degrees between two 3D vectors v1 and v2.
    """
    dot_val = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 * norm_v2 < 1e-12:
        return 0.0
    cos_theta = dot_val / (norm_v1 * norm_v2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return np.degrees(np.arccos(cos_theta))

##############################################################################
# 5') STORE REFERENCE QUATERNIONS (FRAME=0) & ADJUST IMU-2
##############################################################################

reference_quaternions = {}
for imu_id, df_imu in processed_data.items():
    row0 = df_imu.iloc[0]
    q_ref = np.array([row0["q1"], row0["q2"], row0["q3"], row0["q0"]])  # reorder => [x,y,z,w]
    reference_quaternions[imu_id] = q_ref

# --- NEW: For IMU-2, define an explicit +90° offset about Z, then multiply:
if "IMU-2" in reference_quaternions:
    R_ref_2 = R.from_quat(reference_quaternions["IMU-2"])
    R_offset = R.from_euler('z', 90, degrees=True)  # +90° yaw
    # Multiply the old reference by the offset
    R_newRef_2 = R_ref_2 * R_offset
    # Overwrite the stored quaternion with the new reference
    reference_quaternions["IMU-2"] = R_newRef_2.as_quat()  # still [x,y,z,w]

##############################################################################
# 5'') EXTENDED MOVEMENT LOGGING
##############################################################################

movement_records = []

def record_movement(frame, imu_id, roll_diff, pitch_diff, yaw_diff):
    """
    Store the angles in a global list so we can save to CSV later.
    """
    row_data = [
        frame,
        imu_id,
        roll_diff,
        pitch_diff,
        yaw_diff
    ]
    movement_records.append(row_data)

##############################################################################
# 6) ANIMATION UPDATE FUNCTION
##############################################################################

def update(frame):
    for imu_id, (parent_id, seg_length) in imu_hierarchy.items():
        if imu_id not in processed_data or parent_id not in segment_positions:
            continue

        quats = processed_data[imu_id][["q0", "q1", "q2", "q3"]].values
        if frame >= len(quats):
            continue

        # Current orientation
        q_cur = quats[frame, [1,2,3,0]]  # reorder => [x,y,z,w]
        R_cur = R.from_quat(q_cur)

        # Retrieve reference orientation (with offset if IMU-2)
        q_ref = reference_quaternions[imu_id]  
        R_ref = R.from_quat(q_ref)

        # Relative rotation wrt the (possibly offset) reference
        R_diff = R_ref.inv() * R_cur
        roll_diff, pitch_diff, yaw_diff = R_diff.as_euler('xyz', degrees=True)

        # Save angles to global list
        record_movement(frame, imu_id, roll_diff, pitch_diff, yaw_diff)

        # Update skeleton position
        parent_pos = segment_positions[parent_id]
        child_vec = unit_vectors[imu_id] * seg_length
        child_pos = R_cur.apply(child_vec) + parent_pos
        segment_positions[imu_id] = child_pos

    # 3D skeleton lines
    for imu_id, (parent_id, _) in imu_hierarchy.items():
        if imu_id in segment_positions and parent_id in segment_positions:
            p_pos = segment_positions[parent_id]
            c_pos = segment_positions[imu_id]
            lines[imu_id].set_data([p_pos[0], c_pos[0]],
                                   [p_pos[1], c_pos[1]])
            lines[imu_id].set_3d_properties([p_pos[2], c_pos[2]])

    # Shoulder & elbow absolute angles for the right subplot
    current_shoulder = None
    if ("IMU-6" in segment_positions and "IMU-5" in segment_positions
        and "IMU-4" in segment_positions and "IMU-3" in segment_positions):
        v_chest = segment_positions["IMU-6"] - segment_positions["IMU-5"]
        v_upper = segment_positions["IMU-3"] - segment_positions["IMU-4"]
        current_shoulder = angle_between(v_chest, v_upper)

    current_elbow = None
    if ("IMU-4" in segment_positions and "IMU-3" in segment_positions
        and "IMU-2" in segment_positions):
        v_upper_arm = segment_positions["IMU-4"] - segment_positions["IMU-3"]
        v_forearm   = segment_positions["IMU-2"] - segment_positions["IMU-3"]
        current_elbow = angle_between(v_upper_arm, v_forearm)

    if current_shoulder is not None:
        shoulder_angles[frame] = current_shoulder
    if current_elbow is not None:
        elbow_angles[frame] = current_elbow

    angle_line_shoulder.set_data(np.arange(frame + 1), shoulder_angles[:frame + 1])
    angle_line_elbow.set_data(np.arange(frame + 1), elbow_angles[:frame + 1])
    axAng.relim()
    axAng.autoscale_view()

    return list(lines.values()) + [angle_line_shoulder, angle_line_elbow]

##############################################################################
# 7) RUN THE ANIMATION
##############################################################################

ax3d.set_xlim(-0.1, 0.4)
ax3d.set_ylim(-0.75, 0.5)
ax3d.set_zlim(-0.1, 0.4)
ax3d.view_init(elev=11, azim=-151)
set_axes_equal(ax3d)

ani = FuncAnimation(fig, update, frames=num_frames, interval=1, blit=False)
plt.show()

##############################################################################
# 8) SAVE LOGGED DATA TO CSV
##############################################################################

columns = [
    "frame",
    "IMU_ID",
    "roll_deg",
    "pitch_deg",
    "yaw_deg"
]

df_out = pd.DataFrame(movement_records, columns=columns)
df_out.to_csv("movement_angles_with_IMU2_offset.csv", index=False)
print("Saved angles to 'movement_angles_with_IMU2_offset.csv'")
