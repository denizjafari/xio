import time
import os
import csv
import threading
from pynput import keyboard

import ximu3  # Make sure ximu3 library is installed

###############################################################################
# 1. Define a Connection class that opens a device, registers callbacks, and writes CSV logs
###############################################################################
class Connection:
    def __init__(self, connection_info, log_root="LoggedData"):
        # Create xIMU3 Connection object
        self.__connection = ximu3.Connection(connection_info)

        # Open device
        if self.__connection.open() != ximu3.RESULT_OK:
            raise Exception(f"Unable to open {connection_info.to_string()}")

        # Send ping so the device starts sending to our IP
        ping_response = self.__connection.ping()
        if ping_response.result != ximu3.RESULT_OK:
            raise Exception(f"Ping failed for {connection_info.to_string()}")

        # Identify device name and serial number from ping
        self.device_name = ping_response.device_name
        self.serial_number = ping_response.serial_number
        self.__prefix = f"{self.device_name} {self.serial_number}"

        # Create a per-device folder for CSV logs
        self.log_dir = os.path.join(log_root, f"{self.device_name}_{self.serial_number}")
      
        os.makedirs(self.log_dir, exist_ok=True)

        # ---------------------------------------------------------------------
        # Open or create each CSV file needed for logging
        # ---------------------------------------------------------------------
        # Inertial.csv
        self.inertial_file = open(os.path.join(self.log_dir, "Inertial.csv"), mode="a", newline="")
        self.inertial_writer = csv.writer(self.inertial_file)
        if os.stat(self.inertial_file.name).st_size == 0:
            self.inertial_writer.writerow(["timestamp", "gyroX_deg_s", "gyroY_deg_s", "gyroZ_deg_s",
                                           "accX_g", "accY_g", "accZ_g"])

        # Magnetometer.csv
        self.magnetometer_file = open(os.path.join(self.log_dir, "Magnetometer.csv"), mode="a", newline="")
        self.magnetometer_writer = csv.writer(self.magnetometer_file)
        if os.stat(self.magnetometer_file.name).st_size == 0:
            self.magnetometer_writer.writerow(["timestamp", "magX_au", "magY_au", "magZ_au"])

        # Quaternion.csv
        self.quaternion_file = open(os.path.join(self.log_dir, "Quaternion.csv"), mode="a", newline="")
        self.quaternion_writer = csv.writer(self.quaternion_file)
        if os.stat(self.quaternion_file.name).st_size == 0:
            self.quaternion_writer.writerow(["timestamp", "q0", "q1", "q2", "q3"])

        # RotationMatrix.csv
        self.rotation_file = open(os.path.join(self.log_dir, "RotationMatrix.csv"), mode="a", newline="")
        self.rotation_writer = csv.writer(self.rotation_file)
        if os.stat(self.rotation_file.name).st_size == 0:
            self.rotation_writer.writerow(["timestamp","R11","R12","R13","R21","R22","R23","R31","R32","R33"])

        # EulerAngles.csv
        self.euler_file = open(os.path.join(self.log_dir, "EulerAngles.csv"), mode="a", newline="")
        self.euler_writer = csv.writer(self.euler_file)
        if os.stat(self.euler_file.name).st_size == 0:
            self.euler_writer.writerow(["timestamp", "roll_deg", "pitch_deg", "yaw_deg"])

        # LinearAcceleration.csv
        self.linear_file = open(os.path.join(self.log_dir, "LinearAcceleration.csv"), mode="a", newline="")
        self.linear_writer = csv.writer(self.linear_file)
        if os.stat(self.linear_file.name).st_size == 0:
            self.linear_writer.writerow(["timestamp", "linAccX_g", "linAccY_g", "linAccZ_g"])

        # EarthAcceleration.csv
        self.earth_file = open(os.path.join(self.log_dir, "EarthAcceleration.csv"), mode="a", newline="")
        self.earth_writer = csv.writer(self.earth_file)
        if os.stat(self.earth_file.name).st_size == 0:
            self.earth_writer.writerow(["timestamp", "earthAccX_g", "earthAccY_g", "earthAccZ_g"])

        # AhrsStatus.csv
        self.ahrs_file = open(os.path.join(self.log_dir, "AhrsStatus.csv"), mode="a", newline="")
        self.ahrs_writer = csv.writer(self.ahrs_file)
        if os.stat(self.ahrs_file.name).st_size == 0:
            self.ahrs_writer.writerow(["timestamp","initialising","angular_rate_recovery",
                                       "acceleration_recovery","magnetic_recovery"])

        # HighGAccelerometer.csv
        self.highg_file = open(os.path.join(self.log_dir, "HighGAccelerometer.csv"), mode="a", newline="")
        self.highg_writer = csv.writer(self.highg_file)
        if os.stat(self.highg_file.name).st_size == 0:
            self.highg_writer.writerow(["timestamp", "hgAccX_g", "hgAccY_g", "hgAccZ_g"])

        # Temperature.csv
        self.temp_file = open(os.path.join(self.log_dir, "Temperature.csv"), mode="a", newline="")
        self.temp_writer = csv.writer(self.temp_file)
        if os.stat(self.temp_file.name).st_size == 0:
            self.temp_writer.writerow(["timestamp", "temperature_C"])

        # Battery.csv
        self.battery_file = open(os.path.join(self.log_dir, "Battery.csv"), mode="a", newline="")
        self.battery_writer = csv.writer(self.battery_file)
        if os.stat(self.battery_file.name).st_size == 0:
            self.battery_writer.writerow(["timestamp", "battery_%", "voltage_V", "charging_status"])

        # Rssi.csv
        self.rssi_file = open(os.path.join(self.log_dir, "Rssi.csv"), mode="a", newline="")
        self.rssi_writer = csv.writer(self.rssi_file)
        if os.stat(self.rssi_file.name).st_size == 0:
            self.rssi_writer.writerow(["timestamp", "rssi_%", "rssi_dBm"])

        # SerialAccessory.csv
        self.serial_acc_file = open(os.path.join(self.log_dir, "SerialAccessory.csv"), mode="a", newline="")
        self.serial_acc_writer = csv.writer(self.serial_acc_file)
        if os.stat(self.serial_acc_file.name).st_size == 0:
            self.serial_acc_writer.writerow(["timestamp", "data"])

        # Notification.csv
        self.notification_file = open(os.path.join(self.log_dir, "Notification.csv"), mode="a", newline="")
        self.notification_writer = csv.writer(self.notification_file)
        if os.stat(self.notification_file.name).st_size == 0:
            self.notification_writer.writerow(["timestamp", "notification"])

        # Error.csv
        self.error_file = open(os.path.join(self.log_dir, "Error.csv"), mode="a", newline="")
        self.error_writer = csv.writer(self.error_file)
        if os.stat(self.error_file.name).st_size == 0:
            self.error_writer.writerow(["timestamp", "error_description"])

        # ---------------------------------------------------------------------
        # Register the callbacks
        # ---------------------------------------------------------------------
        self.__connection.add_inertial_callback(self.__inertial_callback)
        self.__connection.add_magnetometer_callback(self.__magnetometer_callback)
        self.__connection.add_quaternion_callback(self.__quaternion_callback)
        self.__connection.add_rotation_matrix_callback(self.__rotation_matrix_callback)
        self.__connection.add_euler_angles_callback(self.__euler_angles_callback)
        self.__connection.add_linear_acceleration_callback(self.__linear_acceleration_callback)
        self.__connection.add_earth_acceleration_callback(self.__earth_acceleration_callback)
        self.__connection.add_ahrs_status_callback(self.__ahrs_status_callback)
        self.__connection.add_high_g_accelerometer_callback(self.__high_g_accelerometer_callback)
        self.__connection.add_temperature_callback(self.__temperature_callback)
        self.__connection.add_battery_callback(self.__battery_callback)
        self.__connection.add_rssi_callback(self.__rssi_callback)
        self.__connection.add_serial_accessory_callback(self.__serial_accessory_callback)
        self.__connection.add_notification_callback(self.__notification_callback)
        self.__connection.add_error_callback(self.__error_callback)

    def close(self):
        """Close all CSV files and the device connection."""
        # Inertial
        self.inertial_file.close()
        # Magnetometer
        self.magnetometer_file.close()
        # Quaternion
        self.quaternion_file.close()
        # RotationMatrix
        self.rotation_file.close()
        # EulerAngles
        self.euler_file.close()
        # LinearAcceleration
        self.linear_file.close()
        # EarthAcceleration
        self.earth_file.close()
        # AhrsStatus
        self.ahrs_file.close()
        # HighGAccelerometer
        self.highg_file.close()
        # Temperature
        self.temp_file.close()
        # Battery
        self.battery_file.close()
        # Rssi
        self.rssi_file.close()
        # SerialAccessory
        self.serial_acc_file.close()
        # Notification
        self.notification_file.close()
        # Error
        self.error_file.close()

        self.__connection.close()

    def send_command(self, key, value=None):
        """Optional method to send commands to the xIMU3 device."""
        if value is None:
            value = "null"
        elif type(value) is bool:
            value = str(value).lower()
        elif type(value) is str:
            value = f'"{value}"'
        else:
            value = str(value)

        command = f'{{"{key}":{value}}}'
        responses = self.__connection.send_commands([command], 2, 500)

        if not responses:
            raise Exception(f"No response to {command} for {self.__connection.get_info().to_string()}")
        else:
            print(self.__prefix + " : " + responses[0])

    # -------------------------------------------------------------------------
    # Callbacks: each callback writes one row to its respective CSV file
    # -------------------------------------------------------------------------
    def __inertial_callback(self, message):
        row = [
            message.timestamp,
            message.gyroX,
            message.gyroY,
            message.gyroZ,
            message.accX,
            message.accY,
            message.accZ
        ]
        self.inertial_writer.writerow(row)

    def __magnetometer_callback(self, message):
        row = [
            message.timestamp,
            message.magX,
            message.magY,
            message.magZ
        ]
        self.magnetometer_writer.writerow(row)

    def __quaternion_callback(self, message):
        row = [
            message.timestamp,
            message.q0,
            message.q1,
            message.q2,
            message.q3
        ]
        self.quaternion_writer.writerow(row)

    def __rotation_matrix_callback(self, message):
        row = [
            message.timestamp,
            message.R11,
            message.R12,
            message.R13,
            message.R21,
            message.R22,
            message.R23,
            message.R31,
            message.R32,
            message.R33
        ]
        self.rotation_writer.writerow(row)

    def __euler_angles_callback(self, message):
        row = [
            message.timestamp,
            message.roll,
            message.pitch,
            message.yaw
        ]
        self.euler_writer.writerow(row)

    def __linear_acceleration_callback(self, message):
        row = [
            message.timestamp,
            message.linAccX,
            message.linAccY,
            message.linAccZ
        ]
        self.linear_writer.writerow(row)

    def __earth_acceleration_callback(self, message):
        row = [
            message.timestamp,
            message.earthAccX,
            message.earthAccY,
            message.earthAccZ
        ]
        self.earth_writer.writerow(row)

    def __ahrs_status_callback(self, message):
        row = [
            message.timestamp,
            bool(message.initialising),
            bool(message.angularRateRecovery),
            bool(message.accelerationRecovery),
            bool(message.magneticRecovery)
        ]
        self.ahrs_writer.writerow(row)

    def __high_g_accelerometer_callback(self, message):
        row = [
            message.timestamp,
            message.hgAccX,
            message.hgAccY,
            message.hgAccZ
        ]
        self.highg_writer.writerow(row)

    def __temperature_callback(self, message):
        row = [
            message.timestamp,
            message.value
        ]
        self.temp_writer.writerow(row)

    def __battery_callback(self, message):
        row = [
            message.timestamp,
            message.battery_level,
            message.voltage,
            message.charging_status
        ]
        self.battery_writer.writerow(row)

    def __rssi_callback(self, message):
        row = [
            message.timestamp,
            message.rssi_percentage,
            message.rssi_dBm
        ]
        self.rssi_writer.writerow(row)

    def __serial_accessory_callback(self, message):
        row = [
            message.timestamp,
            message.data
        ]
        self.serial_acc_writer.writerow(row)

    def __notification_callback(self, message):
        row = [
            message.timestamp,
            message.description
        ]
        self.notification_writer.writerow(row)

    def __error_callback(self, message):
        row = [
            message.timestamp,
            message.description
        ]
        self.error_writer.writerow(row)

###############################################################################
# 2. Define helper functions for keyboard monitoring (press 'q' to quit)
###############################################################################
def on_press(key, stop_event):
    """Callback for pynput's keyboard listener. Stops the program on 'q' press."""
    try:
        if key.char == 'q':
            print("Stopping connections...")
            stop_event.set()
            return False  # Stop listener
    except AttributeError:
        # If it's a special key (e.g., arrow key), ignore
        pass

def monitor_key_press(stop_event):
    """Run a keyboard listener that sets an event when 'q' is pressed."""
    with keyboard.Listener(on_press=lambda key: on_press(key, stop_event)) as listener:
        listener.join()

###############################################################################
# 3. Main script: discover devices, start streaming, log data, quit on 'q'
###############################################################################
if __name__ == "__main__":
    # Discover xIMU3 devices via UDP
    discovered = ximu3.NetworkAnnouncement().get_messages_after_short_delay()
    connections = [Connection(m.to_udp_connection_info()) for m in discovered]

    if not connections:
        raise Exception("No UDP connections available.")

    # Optional: send some commands to configure each device
    """
    for conn in connections:
        conn.send_command("udpDataMessagesEnabled", True)
        conn.send_command("inertialMessageRateDivisor", 8)
        # ... etc.
    """

    # Start a separate thread to monitor for 'q' key press
    stop_event = threading.Event()
    key_thread = threading.Thread(target=monitor_key_press, args=(stop_event,))
    key_thread.start()

    try:
        # Main loop: wait until user presses 'q' or we get a KeyboardInterrupt
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()

    # Once we're stopping, ensure the thread finishes
    key_thread.join()

    # Send a shutdown command to each device (optional)
    for conn in connections:
        try:
            conn.send_command("shutdown")
            time.sleep(0.2)
        except:
            pass

    # Close each connection (this also closes CSV files)
    for conn in connections:
        conn.close()

    print("All data streams stopped and CSV files closed.")
