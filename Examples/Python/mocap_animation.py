import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.animation as animation


###############################################
# VICON DATA PROCESSING FUNCTIONS
###############################################

def load_vicon_data(file_path):
    """Loads VICON data from a CSV file (200 Hz)."""
    df = pd.read_csv(file_path)
    df.insert(0, 'Frame', range(1, len(df) + 1))  # Create a Frame column
    df = df.apply(pd.to_numeric, errors='coerce')
    df = df[df['Frame'] >= 1].reset_index(drop=True)
    return df


def extract_markers(df):
    """Extracts the real markers from the dataset."""
    # These markers are present in the data
    real_markers = ["Hand", "Wrist_Right", "Wrist_Left", "Forearm", "Elbow", "Arm",
                    "Shoulder", "C7", "T3", "T10", "L1", "LPSI", "RPSI"]
    marker_cols = []
    for marker in real_markers:
        marker_cols.extend([f"{marker}_X", f"{marker}_Y", f"{marker}_Z"])
    return df[['Frame'] + marker_cols].copy(), real_markers


def fill_missing_data(df):
    """Fills missing data using linear interpolation."""
    df.interpolate(method='linear', inplace=True)
    df.fillna(method='bfill', inplace=True)
    return df


def compute_angle(v1, v2):
    """Computes the angle (in degrees) between two vectors."""
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 * norm_v2 < 1e-6:
        return 0.0
    cos_angle = np.clip(dot_product / (norm_v1 * norm_v2), -1.0, 1.0)
    return np.degrees(np.arccos(cos_angle))


###############################################
# LOAD & PREPARE VICON DATA
###############################################

vicon_file_path = r"/home/jafarid/code/xio/DataLogger/mocap/NewFile.csv"

df_vicon = load_vicon_data(vicon_file_path)
df_markers, real_markers = extract_markers(df_vicon)
df_filled = fill_missing_data(df_markers)

# For visualization (real markers plus a virtual Wrist_Center: U can Skip)
markers = real_markers + ["Wrist_Center"]

# Define skeleton connections
# • Pelvis triangle: LPSI, RPSI, L1
# • Spine chain: L1 → T10 → T3 → C7 → Shoulder
# • Right arm: Shoulder → Arm → Elbow → Forearm
# • Wrist region: Forearm → Wrist_Center, then Wrist_Center to both wrists and to Hand
connections = [
    # Pelvis triangle
    ("LPSI", "RPSI"),
    ("LPSI", "L1"),
    ("RPSI", "L1"),
    # Spine chain
    ("L1", "T10"),
    ("T10", "T3"),
    ("T3", "C7"),
    ("C7", "Shoulder"),
    # Right arm chain
    ("Shoulder", "Arm"),
    ("Arm", "Elbow"),
    ("Elbow", "Forearm"),
    # Wrist region via virtual Wrist_Center
    ("Forearm", "Wrist_Center"),
    ("Wrist_Center", "Wrist_Left"),
    ("Wrist_Center", "Wrist_Right"),
    ("Wrist_Center", "Hand"),
    ("Hand", "Wrist_Left"),
    ("Hand", "Wrist_Right"),
]

###############################################
# FIGURE & AXES SETUP
###############################################

fig = plt.figure(figsize=(14, 7))
ax3d = fig.add_subplot(121, projection='3d')
ax3d.set_title("Vicon Marker Animation (200 Hz)")
ax3d.set_xlabel("X")
ax3d.set_ylabel("Y")
ax3d.set_zlabel("Z")

ax_angle = fig.add_subplot(122)
ax_angle.set_title("Live Shoulder Angle")
ax_angle.set_xlabel("Frame")
ax_angle.set_ylabel("Angle (deg)")

# Initialize 3D scatter for markers
scatter = ax3d.scatter([], [], [], color='red', s=50)

# Create line objects for each connection
lines = []
for conn in connections:
    line, = ax3d.plot([], [], [], 'bo-', linewidth=2)
    lines.append((conn, line))

# Compute axis limits using only the real markers (exclude Wrist_Center)
all_coords = []
for marker in real_markers:
    x = df_filled[f"{marker}_X"].values
    y = df_filled[f"{marker}_Y"].values
    z = df_filled[f"{marker}_Z"].values
    all_coords.append(np.stack([x, y, z], axis=1))
all_coords = np.concatenate(all_coords, axis=0)
min_coords = np.min(all_coords, axis=0)
max_coords = np.max(all_coords, axis=0)
ax3d.set_xlim(min_coords[0] - 0.1, max_coords[0] + 0.1)
ax3d.set_ylim(min_coords[1] - 0.1, max_coords[1] + 0.1)
ax3d.set_zlim(min_coords[2] - 0.1, max_coords[2] + 0.1)
ax3d.view_init(elev=7, azim=-1)

# Compute a small offset (2% of range) for text labels
range_x = max_coords[0] - min_coords[0]
range_y = max_coords[1] - min_coords[1]
offset_x = 0.02 * range_x
offset_y = 0.02 * range_y

# Create text objects to label each marker (including virtual Wrist_Center)
marker_texts = {}
for marker in markers:
    if marker == "Wrist_Center":
        # Compute initial Wrist_Center as average of Wrist_Right and Wrist_Left (first frame)
        x0 = (df_filled["Wrist_Right_X"].iloc[0] + df_filled["Wrist_Left_X"].iloc[0]) / 2
        y0 = (df_filled["Wrist_Right_Y"].iloc[0] + df_filled["Wrist_Left_Y"].iloc[0]) / 2
        z0 = (df_filled["Wrist_Right_Z"].iloc[0] + df_filled["Wrist_Left_Z"].iloc[0]) / 2
    else:
        x0 = df_filled[f"{marker}_X"].iloc[0]
        y0 = df_filled[f"{marker}_Y"].iloc[0]
        z0 = df_filled[f"{marker}_Z"].iloc[0]
    text = ax3d.text(x0 + offset_x, y0 + offset_y, z0, marker,
                     color='black', fontsize=8, zorder=10, clip_on=False)
    marker_texts[marker] = text

# Set up live shoulder angle plot
angle_line, = ax_angle.plot([], [], 'r-', label="Shoulder Angle")
ax_angle.legend()
angle_data = []
frame_data = []

num_frames = len(df_filled)


###############################################
# UPDATE FUNCTION FOR ANIMATION
###############################################

def update(frame):
    # Update marker positions (including virtual Wrist_Center)
    xs, ys, zs = [], [], []
    for marker in markers:
        if marker == "Wrist_Center":
            # Calculate Wrist_Center from the average of the two wrist markers
            x_val = (df_filled["Wrist_Right_X"].iloc[frame] + df_filled["Wrist_Left_X"].iloc[frame]) / 2
            y_val = (df_filled["Wrist_Right_Y"].iloc[frame] + df_filled["Wrist_Left_Y"].iloc[frame]) / 2
            z_val = (df_filled["Wrist_Right_Z"].iloc[frame] + df_filled["Wrist_Left_Z"].iloc[frame]) / 2
        else:
            x_val = df_filled[f"{marker}_X"].iloc[frame]
            y_val = df_filled[f"{marker}_Y"].iloc[frame]
            z_val = df_filled[f"{marker}_Z"].iloc[frame]
        xs.append(x_val)
        ys.append(y_val)
        zs.append(z_val)
        # Update the marker label position with a small offset
        marker_texts[marker].set_position((x_val + offset_x, y_val + offset_y))
        marker_texts[marker].set_3d_properties(z_val, 'z')
    scatter._offsets3d = (np.array(xs), np.array(ys), np.array(zs))

    # Update skeleton connection lines
    for conn, line in lines:
        m1, m2 = conn
        # Get coordinates for m1
        if m1 == "Wrist_Center":
            x1 = (df_filled["Wrist_Right_X"].iloc[frame] + df_filled["Wrist_Left_X"].iloc[frame]) / 2
            y1 = (df_filled["Wrist_Right_Y"].iloc[frame] + df_filled["Wrist_Left_Y"].iloc[frame]) / 2
            z1 = (df_filled["Wrist_Right_Z"].iloc[frame] + df_filled["Wrist_Left_Z"].iloc[frame]) / 2
        else:
            x1 = df_filled[f"{m1}_X"].iloc[frame]
            y1 = df_filled[f"{m1}_Y"].iloc[frame]
            z1 = df_filled[f"{m1}_Z"].iloc[frame]
        # Get coordinates for m2
        if m2 == "Wrist_Center":
            x2 = (df_filled["Wrist_Right_X"].iloc[frame] + df_filled["Wrist_Left_X"].iloc[frame]) / 2
            y2 = (df_filled["Wrist_Right_Y"].iloc[frame] + df_filled["Wrist_Left_Y"].iloc[frame]) / 2
            z2 = (df_filled["Wrist_Right_Z"].iloc[frame] + df_filled["Wrist_Left_Z"].iloc[frame]) / 2
        else:
            x2 = df_filled[f"{m2}_X"].iloc[frame]
            y2 = df_filled[f"{m2}_Y"].iloc[frame]
            z2 = df_filled[f"{m2}_Z"].iloc[frame]
        line.set_data([x1, x2], [y1, y2])
        line.set_3d_properties([z1, z2])

    # Compute shoulder angle:
    # Use vector from C7 to T3 (v_spine) and vector from Shoulder to Arm (v_marker) {need your thoughts here)
    C7 = np.array([df_filled["T10_X"].iloc[frame], df_filled["T10_Y"].iloc[frame], df_filled["T10_Z"].iloc[frame]])
    T3 = np.array([df_filled["T3_X"].iloc[frame], df_filled["T3_Y"].iloc[frame], df_filled["T3_Z"].iloc[frame]])
    Shoulder = np.array(
        [df_filled["Shoulder_X"].iloc[frame], df_filled["Shoulder_Y"].iloc[frame], df_filled["Shoulder_Z"].iloc[frame]])
    Arm = np.array([df_filled["Arm_X"].iloc[frame], df_filled["Arm_Y"].iloc[frame], df_filled["Arm_Z"].iloc[frame]])
    v_spine = T3 - C7
    v_marker = Arm - Shoulder
    shoulder_angle = compute_angle(v_spine, v_marker)

    # Update live shoulder angle plot
    angle_data.append(shoulder_angle)
    frame_data.append(frame)
    angle_line.set_data(frame_data, angle_data)
    ax_angle.relim()
    ax_angle.autoscale_view()

    return [scatter] + [line for _, line in lines] + [angle_line] + list(marker_texts.values())


# Create the animation (interval=1ms for 200 Hz)
ani = animation.FuncAnimation(fig, update, frames=num_frames, interval=1, blit=False)
plt.show()