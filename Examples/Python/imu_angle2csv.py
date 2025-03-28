import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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
    imu_id = parts[0]  # e.g. "IMU-1", "IMU-2", etc.

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
            print(f"'timestamp' column missing in {imu_id} {data_type}. Found columns: {df.columns.tolist()}")
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
# Renaming: IMU-1 remains "Hand"; IMU-2 is now "Wrist"
imu_labels = {
    "IMU-1": "Hand",
    "IMU-2": "Wrist",
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
# Additional Data Records for New Movements
##############################################################################
elbow_data_records = []            # For elbow flexion/extension (yaw from IMU-2)
wrist_data_records = []            # For wrist pronation/supination (roll from IMU-1 and IMU-2)
shoulder_rotation_data_records = []  # For shoulder rotation (adjusted pitch from IMU-2)

##############################################################################
# 4) MAKE AXES EQUAL IN 3D
##############################################################################

def set_axes_equal(ax):
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
    dot_val = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 * norm_v2 < 1e-12:
        return 0.0
    cos_theta = dot_val / (norm_v1 * norm_v2)
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    return np.degrees(np.arccos(cos_theta))

##############################################################################
# 5') RELATIVE RPY FROM FRAME 0
##############################################################################
# Store reference quaternions for each IMU from frame 0
reference_quaternions = {}
for imu_id, df_imu in processed_data.items():
    row0 = df_imu.iloc[0]  # frame 0
    q_ref = np.array([row0["q1"], row0["q2"], row0["q3"], row0["q0"]])  # reorder to [x, y, z, w]
    reference_quaternions[imu_id] = q_ref

##############################################################################
# 5'') FUNCTION TO INTERPRET SHOULDER & SAVE (IMU-3)
##############################################################################
# For IMU-3 (Upper Arm), interpret pitch (Y axis) as abduction/adduction and yaw (Z axis) as flexion/extension.
shoulder_data_records = []  # each element: [frame, abduction, flexion]

def relative_angle(imu_id, diff_angle, frame):
    """
    For IMU-3:
      - Use diff_angle[1] as abduction/adduction (pitch)
      - Use diff_angle[2] as flexion/extension (yaw)
    """
    diff_roll, diff_pitch, diff_yaw = diff_angle
    if imu_id == "IMU-3":
        shoulder_data_records.append([
            frame,      # frame index
            diff_pitch, # abduction/adduction (pitch)
            diff_yaw    # flexion/extension (yaw)
        ])

##############################################################################
# 6) ANIMATE SKELETON & CAPTURE RELATIVE ANGLES
##############################################################################

def update(frame):
    # Update skeleton positions and compute relative rotations
    for imu_id, (parent_id, seg_length) in imu_hierarchy.items():
        if imu_id not in processed_data or parent_id not in segment_positions:
            continue

        quats = processed_data[imu_id][["q0", "q1", "q2", "q3"]].values
        if frame >= len(quats):
            continue

        q_cur = quats[frame, [1,2,3,0]]  # reorder to [x, y, z, w]
        R_cur = R.from_quat(q_cur)

        # Compute relative rotation: R_ref.inv() * R_cur
        q_ref = reference_quaternions[imu_id]
        R_ref = R.from_quat(q_ref)
        R_diff = R_ref.inv() * R_cur
        roll_diff, pitch_diff, yaw_diff = R_diff.as_euler('xyz', degrees=True)

        # Capture shoulder angles for IMU-3
        relative_angle(imu_id, (roll_diff, pitch_diff, yaw_diff), frame)

        # For IMU-2, capture multiple measurements:
        if imu_id == "IMU-2":
            # (a) Elbow flexion/extension (yaw)
            elbow_data_records.append([frame, yaw_diff])
            
            # (b) Compute shoulder rotation using adjusted reference.
            # Rotate the reference quaternion 90° CCW about the Z axis.
            R_adjust = R.from_euler('z', 90, degrees=True)
            R_ref_adjusted = R_adjust * R_ref  # adjusted reference
            R_diff_adjusted = R_ref_adjusted.inv() * R_cur
            # Extract the pitch component from the adjusted relative rotation.
            _, adjusted_pitch, _ = R_diff_adjusted.as_euler('xyz', degrees=True)
            shoulder_rotation_data_records.append([frame, adjusted_pitch])
            
            # (c) Wrist pronation/supination (roll)
            wrist_data_records.append([frame, "Wrist", roll_diff])

        # For IMU-1, capture wrist pronation/supination (roll)
        if imu_id == "IMU-1":
            wrist_data_records.append([frame, "Hand", roll_diff])

        # Update segment positions based on current rotation
        parent_pos = segment_positions[parent_id]
        child_vec = unit_vectors[imu_id] * seg_length
        child_pos = R_cur.apply(child_vec) + parent_pos
        segment_positions[imu_id] = child_pos

    # Update skeleton lines for visualization
    for imu_id, (parent_id, _) in imu_hierarchy.items():
        if imu_id in segment_positions and parent_id in segment_positions:
            p_pos = segment_positions[parent_id]
            c_pos = segment_positions[imu_id]
            lines[imu_id].set_data([p_pos[0], c_pos[0]],
                                   [p_pos[1], c_pos[1]])
            lines[imu_id].set_3d_properties([p_pos[2], c_pos[2]])

    # Compute "absolute" angles based on segment positions
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
# 8) SAVE RESULTS TO CSV
##############################################################################
# Convert the individual data records to DataFrames
df_shoulder = pd.DataFrame(
    shoulder_data_records, 
    columns=["frame", "shoulder_abductionAdduction_deg", "shoulder_flexionExtension_deg"]
)
df_elbow = pd.DataFrame(
    elbow_data_records, 
    columns=["frame", "elbow_flexion_extension_deg"]
)
df_wrist = pd.DataFrame(
    wrist_data_records, 
    columns=["frame", "sensor", "wrist_pronation_supination_deg"]
)
df_shoulder_rotation = pd.DataFrame(
    shoulder_rotation_data_records,
    columns=["frame", "shoulder_rotation_deg"]
)

# Reshape wrist measurements: use pivot_table to aggregate duplicate entries (mean is used here)
df_wrist_pivot = df_wrist.pivot_table(
    index="frame", 
    columns="sensor", 
    values="wrist_pronation_supination_deg",
    aggfunc='mean'
).reset_index()

df_wrist_pivot.rename(
    columns={
        "Hand": "wrist_pronation_supination_Hand",
        "Wrist": "wrist_pronation_supination_Wrist"
    }, 
    inplace=True
)

# Merge all DataFrames to consolidate joint angle metrics by frame
df_combined = pd.merge(df_shoulder, df_elbow, on="frame", how="outer")
df_combined = pd.merge(df_combined, df_wrist_pivot, on="frame", how="outer")
df_combined = pd.merge(df_combined, df_shoulder_rotation, on="frame", how="outer")

# Save the integrated dataset to a CSV file
df_combined.to_csv("combined_angles.csv", index=False)
print("Saved combined angles to 'combined_angles.csv'")

# To Do List
# 1 same procedure for vicon
# compensation
# thresholds 
