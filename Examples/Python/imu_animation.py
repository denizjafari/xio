import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# For 3D projection
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
# 3) FIGURE 1: 3D Skeleton (Left) + Joint Angles (Right)
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
# 5) ANGLE BETWEEN VECTORS
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
# 5') AVERAGED QUATERNION FOR REFERENCE
##############################################################################

def compute_average_quaternion(df, max_frames=50):
    """
    Computes a simple average over the first 'max_frames' quaternions in [x,y,z,w] form.
    """
    q_sum = np.zeros(4)
    frames_to_use = min(len(df), max_frames)

    for i in range(frames_to_use):
        row = df.iloc[i]
        # [q0,q1,q2,q3] => typically [w,x,y,z], reorder => [x,y,z,w]
        q = np.array([row["q1"], row["q2"], row["q3"], row["q0"]])
        q_sum += q

    q_avg = q_sum / frames_to_use
    norm_val = np.linalg.norm(q_avg)
    if norm_val < 1e-12:
        return np.array([0, 0, 0, 1])  # fallback identity
    return q_avg / norm_val

reference_quaternions = {}
for imu_id, df in processed_data.items():
    reference_quaternions[imu_id] = compute_average_quaternion(df, max_frames=50)

##############################################################################
# 6) FIGURE 2: PLOT EACH IMU's RELATIVE ROLL, PITCH, YAW
##############################################################################

fig2, axs2 = plt.subplots(3, 2, figsize=(10, 8), sharex=True)
fig2.suptitle("IMU Roll, Pitch, Yaw Changes vs. Time")

imu_ids_sorted = sorted(processed_data.keys())  # e.g. ["IMU-1", "IMU-2", ..., "IMU-6"]

imu_rpy_data = {}
lines_rpy = {}
ax_map = {}

for i, imu_id in enumerate(imu_ids_sorted):
    r = i // 2
    c = i % 2
    ax = axs2[r, c]
    ax.set_title(f"{imu_id} R/P/Y (deg)")
    ax.set_xlim(0, num_frames)
    ax.set_ylim(-180, 180)  # Adjust as needed
    ax.set_xlabel("Frame")

    # 3 lines per IMU (roll, pitch, yaw)
    roll_line, = ax.plot([], [], label='Roll')
    pitch_line, = ax.plot([], [], label='Pitch')
    yaw_line, = ax.plot([], [], label='Yaw')

    ax.legend()
    ax_map[imu_id] = ax

    # We'll store the time series of roll/pitch/yaw
    imu_rpy_data[imu_id] = np.zeros((num_frames, 3))
    lines_rpy[imu_id] = (roll_line, pitch_line, yaw_line)


##############################################################################
# 7) UPDATE FUNCTION FOR ANIMATION
##############################################################################

def update(frame):
    # A) Update skeleton positions
    for imu_id, (parent_id, seg_length) in imu_hierarchy.items():
        if imu_id not in processed_data or parent_id not in segment_positions:
            continue

        motion_quats = processed_data[imu_id][["q0", "q1", "q2", "q3"]].values
        if frame >= len(motion_quats):
            continue

        # Current orientation
        q_cur = motion_quats[frame, [1, 2, 3, 0]]
        R_cur = R.from_quat(q_cur)

        # Reference
        q_ref = reference_quaternions[imu_id]
        R_ref = R.from_quat(q_ref)

        # Relative rotation
        R_diff = R_ref.inv() * R_cur
        roll_diff, pitch_diff, yaw_diff = R_diff.as_euler('xyz', degrees=True)

        # Store in array for fig2
        imu_rpy_data[imu_id][frame, 0] = roll_diff
        imu_rpy_data[imu_id][frame, 1] = pitch_diff
        imu_rpy_data[imu_id][frame, 2] = yaw_diff

        # Skeleton child position
        parent_pos = segment_positions[parent_id]
        child_vec = unit_vectors[imu_id] * seg_length
        child_pos = R_cur.apply(child_vec) + parent_pos
        segment_positions[imu_id] = child_pos

    # B) Update skeleton lines
    for imu_id, (parent_id, _) in imu_hierarchy.items():
        if imu_id in segment_positions and parent_id in segment_positions:
            p_pos = segment_positions[parent_id]
            c_pos = segment_positions[imu_id]

            x_data = [p_pos[0], c_pos[0]]
            y_data = [p_pos[1], c_pos[1]]
            z_data = [p_pos[2], c_pos[2]]

            lines[imu_id].set_data(x_data, y_data)
            lines[imu_id].set_3d_properties(z_data)

    # C) Shoulder & elbow angles
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

    # D) Update lines on FIGURE 2 for each IMU
    for imu_id in imu_ids_sorted:
        roll_arr = imu_rpy_data[imu_id][:frame+1, 0]
        pitch_arr= imu_rpy_data[imu_id][:frame+1, 1]
        yaw_arr  = imu_rpy_data[imu_id][:frame+1, 2]

        roll_line, pitch_line, yaw_line = lines_rpy[imu_id]
        roll_line.set_data(np.arange(frame+1), roll_arr)
        pitch_line.set_data(np.arange(frame+1), pitch_arr)
        yaw_line.set_data(np.arange(frame+1), yaw_arr)

        # Auto-scale each subplot if desired
        ax_map[imu_id].relim()
        ax_map[imu_id].autoscale_view()

    # E) Redraw the second figure
    fig2.canvas.draw_idle()

    # Return the lines that changed (for animation)
    updates = list(lines.values()) + [angle_line_shoulder, angle_line_elbow]
    for imu_id in imu_ids_sorted:
        updates += list(lines_rpy[imu_id])
    return updates

##############################################################################
# 8) RUN THE ANIMATION
##############################################################################

# Tweak the 3D skeleton view
ax3d.set_xlim(-0.1, 0.4)
ax3d.set_ylim(-0.75, 0.5)
ax3d.set_zlim(-0.1, 0.4)
ax3d.view_init(elev=11, azim=-151)
set_axes_equal(ax3d)

# Bind animation to FIGURE 1 (the skeleton figure), so it drives the update
ani = FuncAnimation(fig, update, frames=num_frames, interval=1, blit=False)

# Show both figures at once
plt.show()
