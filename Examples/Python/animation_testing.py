# # Version2
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # required for 3D projection
from scipy.spatial.transform import Rotation as R
from matplotlib.animation import FuncAnimation
import matplotlib.gridspec as gridspec
import matplotlib.animation as animation

# 1. Data Reading & Processing
folder_path = r"/home/jafarid/code/xio/DataLogger/2025-02-07_17-55-28"
files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
imu_data = {}

for file in files:
    parts = file.split("_")
    imu_id = parts[0]  # IMU-i
    if "quaternion" in file:
        data_type = "quaternion_log"
    else:
        continue  # Skip non-quaternion files
    file_path = os.path.join(folder_path, file)
    df = pd.read_csv(file_path)
    if "timestamp" not in df.columns:
        if "Time" in df.columns:
            df.rename(columns={"Time": "timestamp"}, inplace=True)
        else:
            print(f" 'timestamp' column missing in {imu_id} {data_type}")
            continue
    if imu_id not in imu_data:
        imu_data[imu_id] = {}
    imu_data[imu_id][data_type] = df

motion_end_time = 5.90e9  # threshold
processed_data = {}
for imu_id, data in imu_data.items():
    if "quaternion_log" in data:
        motion_data = data["quaternion_log"].sort_values("timestamp")
        motion_data = motion_data[motion_data["timestamp"] <= motion_end_time]
        processed_data[imu_id] = motion_data

if not processed_data:
    print("No valid data processed. Please check the input files.")
    exit()


# 2. Skeleton & Hierarchy Setup
# Define the IMU hierarchy as: child: (parent, segment_length)
imu_hierarchy = {
    "IMU-5": ("IMU-6", 0.25),  # Upper Back → Torso
    "IMU-4": ("IMU-5", 0.2),   # Shoulder → Upper Back
    "IMU-3": ("IMU-4", 0.25),  # Upper Arm → Shoulder
    "IMU-2": ("IMU-3", 0.25),  # Forearm → Upper Arm
    "IMU-1": ("IMU-2", 0.25),  # Hand → Forearm
}

# Define unit vectors for each IMU (sensor orientation to make the chain)
unit_vectors = {
    "IMU-6": np.array([-1, 0, 0]),  # Torso (reference)
    "IMU-5": np.array([-1, 0, 0]),
    "IMU-4": np.array([1, 0, 0]),
    "IMU-3": np.array([1, 0, 0]),
    "IMU-2": np.array([1, 0, 0]),
    "IMU-1": np.array([1, 0, 0]),
}

# Define colors and labels for plotting
imu_colors = {
    "IMU-1": "red",
    "IMU-2": "blue",
    "IMU-3": "green",
    "IMU-4": "purple",
    "IMU-5": "orange",
    "IMU-6": "black",  # Torso (reference)
}
imu_labels = {
    "IMU-1": "Hand",
    "IMU-2": "Forearm",
    "IMU-3": "Upper Arm",
    "IMU-4": "Shoulder",
    "IMU-5": "Upper Back",
    "IMU-6": "Torso (Ref)",
}

# The torso is fixed at (0, 0, 0)
torso_id = "IMU-6"
segment_positions = {torso_id: np.array([0, 0, 0])}

# Determine the number of frames based on the smallest dataset
num_frames = min([len(data) for data in processed_data.values()])


# 3. Create a Combined Figure
# Top half will show the 3D skeleton; bottom half will show three subplots for roll, pitch, yaw changes.
fig = plt.figure(figsize=(12, 8))
gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1])
ax_skeleton = fig.add_subplot(gs[0], projection='3d')
ax_skeleton.set_title("3D Skeleton Animation")
ax_skeleton.set_xlim(-1, 1)
ax_skeleton.set_ylim(-1, 1)
ax_skeleton.set_zlim(-1, 1)
ax_skeleton.set_xlabel("X-axis")
ax_skeleton.set_ylabel("Y-axis")
ax_skeleton.set_zlabel("Z-axis")

# Create three subplots for Euler angles (roll, pitch, yaw)
gs_angles = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[1])
ax_roll = fig.add_subplot(gs_angles[0])
ax_pitch = fig.add_subplot(gs_angles[1])
ax_yaw = fig.add_subplot(gs_angles[2])
ax_roll.set_title("Roll Change (°)")
ax_pitch.set_title("Pitch Change (°)")
ax_yaw.set_title("Yaw Change (°)")
for ax in (ax_roll, ax_pitch, ax_yaw):
    ax.set_xlabel("Frame")
    ax.set_xlim(0, num_frames)


# 4. Initialize Artists for Skeleton and Euler Graphs
# Initialize skeleton line objects for each joint in the hierarchy.
lines = {}
for imu_id in imu_hierarchy.keys():
    line, = ax_skeleton.plot([], [], [], 'o-', color=imu_colors[imu_id], label=imu_labels[imu_id])
    lines[imu_id] = line
ax_skeleton.legend(loc='upper right', fontsize=10)

# Initialize text annotations for Euler angles on the skeleton.
angle_texts = {}

# For Euler angle graphs, create one line per joint for each Euler angle.
angle_lines_R = {}
angle_lines_P = {}
angle_lines_Y = {}
for imu_id in imu_hierarchy.keys():
    line_R, = ax_roll.plot([], [], label=imu_labels[imu_id], color=imu_colors[imu_id])
    line_P, = ax_pitch.plot([], [], label=imu_labels[imu_id], color=imu_colors[imu_id])
    line_Y, = ax_yaw.plot([], [], label=imu_labels[imu_id], color=imu_colors[imu_id])
    angle_lines_R[imu_id] = line_R
    angle_lines_P[imu_id] = line_P
    angle_lines_Y[imu_id] = line_Y
ax_roll.legend(fontsize=8)
ax_pitch.legend(fontsize=8)
ax_yaw.legend(fontsize=8)

# Global variables to store the baseline Euler angles (anatomical posture)
baseline_angles = {}  # Will store (roll, pitch, yaw) at frame 0 for each IMU.
time_history = []     # To store frame indices.
angle_history = {}    # For each IMU, store lists for roll, pitch, and yaw differences.
for imu_id in imu_hierarchy.keys():
    angle_history[imu_id] = {'roll': [], 'pitch': [], 'yaw': []}


# 5. Update Function for the Animation
def update(frame):
    global angle_texts, baseline_angles, time_history, angle_history

    # Reset torso position for every frame.
    segment_positions[torso_id] = np.array([0, 0, 0])
    current_angles = {}  # Will store current Euler angles for each IMU.

    # Process each IMU in the hierarchy.
    for imu_id, (parent_id, segment_length) in imu_hierarchy.items():
        if imu_id not in processed_data or parent_id not in segment_positions:
            continue

        # Get quaternion data for this frame (assumes CSV columns [q0, q1, q2, q3]).
        motion_quaternions = processed_data[imu_id][["q0", "q1", "q2", "q3"]].values
        if frame >= len(motion_quaternions):
            continue
        # Rearrange quaternion to [x, y, z, w] for scipy.
        quat = motion_quaternions[frame, [1, 2, 3, 0]]
        motion_rotation = R.from_quat(quat)
        # Convert the quaternion to Euler angles (roll, pitch, yaw) in degrees.
        roll, pitch, yaw = motion_rotation.as_euler('xyz', degrees=True)
        current_angles[imu_id] = (roll, pitch, yaw)
        print(f"Frame {frame} - {imu_id}: R = {roll:.2f}°, P = {pitch:.2f}°, Y = {yaw:.2f}°")

        # Compute the segment's position relative to its parent's position.
        parent_position = segment_positions[parent_id]
        rel_pos = motion_rotation.apply(unit_vectors[imu_id] * segment_length)
        segment_positions[imu_id] = parent_position + rel_pos

    # Update skeleton lines connecting each joint to its parent.
    for imu_id, (parent_id, _) in imu_hierarchy.items():
        if imu_id in segment_positions and parent_id in segment_positions:
            pos = segment_positions[imu_id]
            parent_pos = segment_positions[parent_id]
            x_data = np.array([parent_pos[0], pos[0]])
            y_data = np.array([parent_pos[1], pos[1]])
            z_data = np.array([parent_pos[2], pos[2]])
            lines[imu_id].set_data(x_data, y_data)
            lines[imu_id].set_3d_properties(z_data)

    # Update or create text annotations for Euler angles at each joint (on the skeleton).
    for imu_id, (roll, pitch, yaw) in current_angles.items():
        if imu_id in segment_positions:
            x, y, z = segment_positions[imu_id]
            text_str = f"R: {roll:.2f}\nP: {pitch:.2f}\nY: {yaw:.2f}"
            if imu_id in angle_texts:
                angle_texts[imu_id].set_position((x, y))
                angle_texts[imu_id].set_3d_properties(z, 'z')
                angle_texts[imu_id].set_text(text_str)
            else:
                angle_texts[imu_id] = ax_skeleton.text(x, y, z, text_str, fontsize=8, color=imu_colors[imu_id])

    # At frame 0, store the baseline (anatomical posture) for each IMU.
    if frame == 0:
        for imu_id, angles in current_angles.items():
            baseline_angles[imu_id] = angles

    # Append the current frame to the time history.
    time_history.append(frame)

    # For each joint, compute the difference (delta) from baseline and store in history.
    for imu_id, (roll, pitch, yaw) in current_angles.items():
        base_roll, base_pitch, base_yaw = baseline_angles.get(imu_id, (0, 0, 0))
        d_roll = roll - base_roll
        d_pitch = pitch - base_pitch
        d_yaw = yaw - base_yaw
        angle_history[imu_id]['roll'].append(d_roll)
        angle_history[imu_id]['pitch'].append(d_pitch)
        angle_history[imu_id]['yaw'].append(d_yaw)
        # Update the Euler angle line data.
        angle_lines_R[imu_id].set_data(time_history, angle_history[imu_id]['roll'])
        angle_lines_P[imu_id].set_data(time_history, angle_history[imu_id]['pitch'])
        angle_lines_Y[imu_id].set_data(time_history, angle_history[imu_id]['yaw'])

    # adjusting the y-limits of the Euler plots.
    for ax in (ax_roll, ax_pitch, ax_yaw):
        ax.relim()
        ax.autoscale_view()

    # Collect and return all updated artists.
    artists = list(lines.values()) + list(angle_texts.values())
    for imu_id in imu_hierarchy.keys():
        artists.extend([angle_lines_R[imu_id], angle_lines_P[imu_id], angle_lines_Y[imu_id]])
    return artists

# 6. Create and Run the Animation
ani = FuncAnimation(fig, update, frames=num_frames, interval=5, blit=True)
plt.tight_layout()

# Use FFmpegWriter for .mov format
writer = animation.FFMpegWriter(fps=1, metadata={"artist": "Your Name"})
ani.save("imu_data.mov", writer=writer)

plt.show()
