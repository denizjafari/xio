import time
import os
import csv
import ximu3

###############################################################################
# 1. Callback-based Connection that logs to CSV + prints data
###############################################################################
class Connection:
    def __init__(self, connection_info, log_root="LoggedDataNetwork"):
        """Initialize the xIMU3 connection, create CSV files, register callbacks."""
        self.__connection = ximu3.Connection(connection_info)

        if self.__connection.open() != ximu3.RESULT_OK:
            raise Exception(f"Unable to open {connection_info.to_string()}")

        # Send ping so device knows our IP/port and starts streaming
        ping_response = self.__connection.ping()
        if ping_response.result != ximu3.RESULT_OK:
            raise Exception(f"Ping failed for {connection_info.to_string()}")

        device_name = ping_response.device_name
        serial_number = ping_response.serial_number
        self.__prefix = f"{device_name} {serial_number}"

        # Create a per-device log directory
        self.log_dir = os.path.join(log_root, f"{device_name}_{serial_number}")
        os.makedirs(self.log_dir, exist_ok=True)

        # ---------------------------------------------------------------------
        # Open CSV files for each data type we want to log
        # ---------------------------------------------------------------------
        # 1) Inertial.csv
        self.inertial_file = open(os.path.join(self.log_dir, "Inertial.csv"), mode="a", newline="")
        self.inertial_writer = csv.writer(self.inertial_file)
        if os.stat(self.inertial_file.name).st_size == 0:
            self.inertial_writer.writerow(["timestamp", "gyroX_deg_s", "gyroY_deg_s", "gyroZ_deg_s",
                                           "accX_g", "accY_g", "accZ_g"])

        # 2) Magnetometer.csv
        self.magnet_file = open(os.path.join(self.log_dir, "Magnetometer.csv"), mode="a", newline="")
        self.magnet_writer = csv.writer(self.magnet_file)
        if os.stat(self.magnet_file.name).st_size == 0:
            self.magnet_writer.writerow(["timestamp", "magX_au", "magY_au", "magZ_au"])

        # 3) Quaternion.csv
        self.quaternion_file = open(os.path.join(self.log_dir, "Quaternion.csv"), mode="a", newline="")
        self.quaternion_writer = csv.writer(self.quaternion_file)
        if os.stat(self.quaternion_file.name).st_size == 0:
            self.quaternion_writer.writerow(["timestamp", "q0", "q1", "q2", "q3"])

        # 4) RotationMatrix.csv
        self.rotation_file = open(os.path.join(self.log_dir, "RotationMatrix.csv"), mode="a", newline="")
        self.rotation_writer = csv.writer(self.rotation_file)
        if os.stat(self.rotation_file.name).st_size == 0:
            self.rotation_writer.writerow(["timestamp","R11","R12","R13","R21","R22","R23","R31","R32","R33"])

        # 5) EulerAngles.csv
        self.euler_file = open(os.path.join(self.log_dir, "EulerAngles.csv"), mode="a", newline="")
        self.euler_writer = csv.writer(self.euler_file)
        if os.stat(self.euler_file.name).st_size == 0:
            self.euler_writer.writerow(["timestamp", "roll_deg", "pitch_deg", "yaw_deg"])

        # 6) LinearAcceleration.csv
        self.linear_file = open(os.path.join(self.log_dir, "LinearAcceleration.csv"), mode="a", newline="")
        self.linear_writer = csv.writer(self.linear_file)
        if os.stat(self.linear_file.name).st_size == 0:
            self.linear_writer.writerow(["timestamp", "linAccX_g", "linAccY_g", "linAccZ_g"])

        # 7) EarthAcceleration.csv
        self.earth_file = open(os.path.join(self.log_dir, "EarthAcceleration.csv"), mode="a", newline="")
        self.earth_writer = csv.writer(self.earth_file)
        if os.stat(self.earth_file.name).st_size == 0:
            self.earth_writer.writerow(["timestamp", "earthAccX_g", "earthAccY_g", "earthAccZ_g"])

        # 8) AhrsStatus.csv
        self.ahrs_file = open(os.path.join(self.log_dir, "AhrsStatus.csv"), mode="a", newline="")
        self.ahrs_writer = csv.writer(self.ahrs_file)
        if os.stat(self.ahrs_file.name).st_size == 0:
            self.ahrs_writer.writerow(["timestamp","initialising","angular_rate_recovery",
                                       "acceleration_recovery","magnetic_recovery"])

        # 9) HighGAccelerometer.csv
        self.highg_file = open(os.path.join(self.log_dir, "HighGAccelerometer.csv"), mode="a", newline="")
        self.highg_writer = csv.writer(self.highg_file)
        if os.stat(self.highg_file.name).st_size == 0:
            self.highg_writer.writerow(["timestamp", "hgAccX_g", "hgAccY_g", "hgAccZ_g"])

        # 10) Temperature.csv
        self.temp_file = open(os.path.join(self.log_dir, "Temperature.csv"), mode="a", newline="")
        self.temp_writer = csv.writer(self.temp_file)
        if os.stat(self.temp_file.name).st_size == 0:
            self.temp_writer.writerow(["timestamp", "temperature_C"])

        # 11) Battery.csv
        self.battery_file = open(os.path.join(self.log_dir, "Battery.csv"), mode="a", newline="")
        self.battery_writer = csv.writer(self.battery_file)
        if os.stat(self.battery_file.name).st_size == 0:
            self.battery_writer.writerow(["timestamp", "battery_%", "voltage_V", "charging_status"])

        # 12) Rssi.csv
        self.rssi_file = open(os.path.join(self.log_dir, "Rssi.csv"), mode="a", newline="")
        self.rssi_writer = csv.writer(self.rssi_file)
        if os.stat(self.rssi_file.name).st_size == 0:
            self.rssi_writer.writerow(["timestamp", "rssi_%", "rssi_dBm"])

        # 13) SerialAccessory.csv
        self.serial_acc_file = open(os.path.join(self.log_dir, "SerialAccessory.csv"), mode="a", newline="")
        self.serial_acc_writer = csv.writer(self.serial_acc_file)
        if os.stat(self.serial_acc_file.name).st_size == 0:
            self.serial_acc_writer.writerow(["timestamp", "data"])

        # 14) Notification.csv
        self.notification_file = open(os.path.join(self.log_dir, "Notification.csv"), mode="a", newline="")
        self.notification_writer = csv.writer(self.notification_file)
        if os.stat(self.notification_file.name).st_size == 0:
            self.notification_writer.writerow(["timestamp", "notification"])

        # 15) Error.csv
        self.error_file = open(os.path.join(self.log_dir, "Error.csv"), mode="a", newline="")
        self.error_writer = csv.writer(self.error_file)
        if os.stat(self.error_file.name).st_size == 0:
            self.error_writer.writerow(["timestamp", "error_description"])

        # Register callbacks for all data streams
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
        """Close CSV files and the device connection."""
        self.inertial_file.close()
        self.magnet_file.close()
        self.quaternion_file.close()
        self.rotation_file.close()
        self.euler_file.close()
        self.linear_file.close()
        self.earth_file.close()
        self.ahrs_file.close()
        self.highg_file.close()
        self.temp_file.close()
        self.battery_file.close()
        self.rssi_file.close()
        self.serial_acc_file.close()
        self.notification_file.close()
        self.error_file.close()

        self.__connection.close()

    def send_command(self, key, value=None):
        """Send xIMU3 JSON command and print the response."""
        if value is None:
            value = "null"
        elif isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, str):
            value = f'"{value}"'
        else:
            value = str(value)

        command = f'{{"{key}":{value}}}'
        responses = self.__connection.send_commands([command], 2, 500)

        if not responses:
            raise Exception(f"No response to {command} for {self.__connection.get_info().to_string()}")
        else:
            print(self.__prefix, ":", responses[0])

    # -------------------------------------------------------------------------
    # Callbacks: we both print the data and write it to CSV
    # -------------------------------------------------------------------------
    def __inertial_callback(self, message):
        print(self.__prefix, message.to_string())
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
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.magX,
            message.magY,
            message.magZ
        ]
        self.magnet_writer.writerow(row)

    def __quaternion_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.q0,
            message.q1,
            message.q2,
            message.q3
        ]
        self.quaternion_writer.writerow(row)

    def __rotation_matrix_callback(self, message):
        print(self.__prefix, message.to_string())
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
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.roll,
            message.pitch,
            message.yaw
        ]
        self.euler_writer.writerow(row)

    def __linear_acceleration_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.linAccX,
            message.linAccY,
            message.linAccZ
        ]
        self.linear_writer.writerow(row)

    def __earth_acceleration_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.earthAccX,
            message.earthAccY,
            message.earthAccZ
        ]
        self.earth_writer.writerow(row)

    def __ahrs_status_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            bool(message.initialising),
            bool(message.angularRateRecovery),
            bool(message.accelerationRecovery),
            bool(message.magneticRecovery)
        ]
        self.ahrs_writer.writerow(row)

    def __high_g_accelerometer_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.hgAccX,
            message.hgAccY,
            message.hgAccZ
        ]
        self.highg_writer.writerow(row)

    def __temperature_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.value
        ]
        self.temp_writer.writerow(row)

    def __battery_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.battery_level,
            message.voltage,
            message.charging_status
        ]
        self.battery_writer.writerow(row)

    def __rssi_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.rssi_percentage,
            message.rssi_dBm
        ]
        self.rssi_writer.writerow(row)

    def __serial_accessory_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.data
        ]
        self.serial_acc_writer.writerow(row)

    def __notification_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.description
        ]
        self.notification_writer.writerow(row)

    def __error_callback(self, message):
        print(self.__prefix, message.to_string())
        row = [
            message.timestamp,
            message.description
        ]
        self.error_writer.writerow(row)


###############################################################################
# 2. Main script using NetworkAnnouncement and the Connection class above
###############################################################################
if __name__ == "__main__":
    # Discover xIMU3 devices on the network
    announcements = ximu3.NetworkAnnouncement().get_messages_after_short_delay()
    print(announcements)
    print('HEERE')
    connections = [Connection(m.to_udp_connection_info()) for m in announcements]
    print(connections[0])
    print('now here')
    if not connections:
        raise Exception("No UDP devices found via network.")

    # Example: send some commands
    #for conn in connections:
    #    conn.send_command("strobe")
    #    conn.send_command("note", "Hello World!")
    #    conn.send_command("udpDataMessagesEnabled", True)
    #    conn.send_command("inertialMessageRateDivisor", 8)

    # Let data stream for 60 seconds
    print("Logging data for 60 seconds...")
    time.sleep(60)

    # Close all connections (this also closes CSV files)
    for conn in connections:
        conn.close()
    print("All connections closed. CSV logs saved in 'LoggedDataNetwork/'.")
