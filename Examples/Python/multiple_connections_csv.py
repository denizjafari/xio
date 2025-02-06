import time
import ximu3
import csv


class Connection:
    def __init__(self, connection_info, csv_writer=None):
        
        # Save the CSV writer (if provided) as an instance variable.
        self.csv_writer = csv_writer
        
        self.__connection = ximu3.Connection(connection_info)

        if self.__connection.open() != ximu3.RESULT_OK:
            raise Exception(f"Unable to open {connection_info.to_string()}")

        ping_response = self.__connection.ping()  # send ping so that device starts sending to computer's IP address

        if ping_response.result != ximu3.RESULT_OK:
            raise Exception(f"Ping failed for {connection_info.to_string()}")

        self.__prefix = f"{ping_response.device_name} {ping_response.serial_number} "

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
        self.__connection.close()

    def send_command(self, key, value=None):
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
            print(self.__prefix + responses[0])

    def __inertial_callback(self, message):
        print("Inertial callback invoked!")
        print(self.__prefix + message.to_string())

    def __magnetometer_callback(self, message):
        print("Magnetometer callback invoked!")
        print(self.__prefix + message.to_string())

    def __quaternion_callback(self, message):
        print("Quaternion callback invoked!")
        #timestamp = time.time()  # Get current time as timestamp.
        data_str = message.to_string()  # Get string representation of the quaternion.
        parts = data_str.split()
        
        if len(parts) < 4:
            print("Unexpected quaternion message format:", data_str)
            return
        print('testing here')
        q0, q1, q2, q3 = parts[-4:]
        timestamp = parts[0]
       
        device_name = self.__prefix.split()[0]
        
        if self.csv_writer is not None:
            # Write a CSV row with the timestamp, device prefix, and quaternion data.
            self.csv_writer.writerow([device_name, timestamp, q0, q1, q2, q3])
            if hasattr(self, 'csv_file'):
                self.csv_file.flush()
        else:
            print(device_name + " Timestamp: " + str(timestamp) + " Quaternion: " + f"{q0} {q1} {q2} {q3}")

    def __rotation_matrix_callback(self, message):
        print("Rotation Matrix callback invoked!")
        print(self.__prefix + message.to_string())
        #print('HEEEREEEEE: ', message.R11)

    def __euler_angles_callback(self, message):
        print("Euler Angles callback invoked!")
        print(self.__prefix + message.to_string())

    def __linear_acceleration_callback(self, message):
        print("Linear Acc callback invoked!")
        print(self.__prefix + message.to_string())

    def __earth_acceleration_callback(self, message):
        print("Earth Acc callback invoked!")
        print(self.__prefix + message.to_string())

    def __ahrs_status_callback(self, message):
        print(self.__prefix + message.to_string())

    def __high_g_accelerometer_callback(self, message):
        print("High g Acc callback invoked!")
        print(self.__prefix + message.to_string())

    def __temperature_callback(self, message):
        print("temp callback invoked!")
        print(self.__prefix + message.to_string())

    def __battery_callback(self, message):
        print("battery callback invoked!")
        print(self.__prefix + message.to_string())

    def __rssi_callback(self, message):
        print("RSSI callback invoked!")
        print(self.__prefix + message.to_string())

    def __serial_accessory_callback(self, message):
        print("Serial Access callback invoked!")
        print(self.__prefix + message.to_string())

    def __notification_callback(self, message):
        print("Notification callback invoked!")
        print(self.__prefix + message.to_string())

    def __error_callback(self, message):
        print("Error callback invoked!")
        print(self.__prefix + message.to_string())


# Open a CSV file to log quaternion data.
csv_file = open("quaternion_log.csv", "w", newline="")
csv_writer = csv.writer(csv_file)
# Write header row: timestamp, device prefix, and quaternion data.
csv_writer.writerow(["device", "timestamp", "q0", "q1", "q2", "q3"])


connections = [Connection(m.to_udp_connection_info(), csv_writer=csv_writer) for m in ximu3.NetworkAnnouncement().get_messages_after_short_delay()]

if not connections:
    raise Exception("No UDP connections available")

for connection in connections:
    #connection.send_command("strobe")  # example command with null value
    #connection.send_command("note", "Hello World!")  # example command with string value
    connection.send_command("udpDataMessagesEnabled", True)  # example command with true/false value
    connection.send_command("inertialMessageRateDivisor", 8)  # example command with number value

time.sleep(3)

for connection in connections:
    connection.close()

# Close the CSV file.
csv_file.close()