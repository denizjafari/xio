import time
import ximu3
import csv


class Connection:
    def __init__(self, connection_info):
        
        
        
        self.__connection = ximu3.Connection(connection_info)

        if self.__connection.open() != ximu3.RESULT_OK:
            raise Exception(f"Unable to open {connection_info.to_string()}")

        ping_response = self.__connection.ping()  # send ping so that device starts sending to computer's IP address

        if ping_response.result != ximu3.RESULT_OK:
            raise Exception(f"Ping failed for {connection_info.to_string()}")

        self.__prefix = f"{ping_response.device_name} {ping_response.serial_number} "
        
        device_name = ping_response.device_name.strip()
        serial = ping_response.serial_number.strip()
        
       
      
        self.__connection.add_ahrs_status_callback(self.__ahrs_status_callback)
        self.__connection.add_temperature_callback(self.__temperature_callback)
        self.__connection.add_battery_callback(self.__battery_callback)
        self.__connection.add_rssi_callback(self.__rssi_callback)
        self.__connection.add_serial_accessory_callback(self.__serial_accessory_callback)
        self.__connection.add_notification_callback(self.__notification_callback)
        
 
        
        # Dictionaries to store CSV file handles and writers.
        self.csv_files = {}
        self.csv_writers = {}
        
        # Define a configuration for each callback.
        # Each entry provides:
        #  - a CSV header (list of column names)
        #  - a parser function that takes a message and returns a list of row values
        #  - the name of the connection registration method
        self.callback_configs = {
            "inertial": {
                "header": ["device", "timestamp", "gyro_x [deg/s]", "gyro_y [deg/s]", "gyro_z [deg/s]", "acc_x [g]", "acc_y [g]", "acc_z [g]"],
                "parser": self.parse_inertial,
                "register_method": "add_inertial_callback"
            },
            "magnetometer": {
                "header": ["device", "timestamp", "mag_x [a.u.]", "mag_y [a.u.]", "mag_z [a.u.]"],
                "parser": self.parse_magnetometer,
                "register_method": "add_magnetometer_callback"
            },
            "quaternion": {
                "header": ["device", "timestamp", "q0", "q1", "q2", "q3"],
                "parser": self.parse_quaternion,
                "register_method": "add_quaternion_callback"
            },
            "rotation_matrix": {
                "header": ["device", "timestamp", "R_xx","R_xy", "R_xz", "R_yx","R_yy","R_yz","R_zx","R_zy","R_zz"],
                "parser": self.parse_rotation,
                "register_method": "add_rotation_matrix_callback"
            },
            "euler_angles": {
                "header": ["device", "timestamp", "Roll [deg]","Pitch [deg]", "Yaw [deg]"],
                "parser": self.parse_euler,
                "register_method": "add_euler_angles_callback"
            },
            "linear_acceleration": {
                "header": ["device", "timestamp", "q0", "q1", "q2", "q3", "acc_x [g]", "acc_y [g]", "acc_z [g]"],
                "parser": self.parse_linear_acc,
                "register_method": "add_linear_acceleration_callback"
            },
            "earth_acceleration": {
                "header": ["device", "timestamp", "q0", "q1", "q2", "q3", "E_acc_x [g]", "E_acc_y [g]", "E_acc_z [g]"],
                "parser": self.parse_earth_linear_acc,
                "register_method": "add_earth_acceleration_callback"
            },
        
            "high_g_accelerometer": {
                "header": ["device", "timestamp", "high-g_acc_x [g]", "high-g_acc_y [g]", "high-g_acc_z [g]"],
                "parser": self.parse_high_g,
                "register_method": "add_high_g_accelerometer_callback"
            },
            
            "error": {
                "header": ["error_message"],
                "parser": self.parse_error,
                "register_method": "add_error_callback"
            }
        }
        
        # For each callback type, create a unique CSV file and register the callback.
        for cb_name, config in self.callback_configs.items():
            filename = f"{device_name}_{serial}_{cb_name}_log.csv"
            csv_file = open(filename, "w", newline="")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(config["header"])
            self.csv_files[cb_name] = csv_file
            self.csv_writers[cb_name] = csv_writer
            print(f"Created CSV file for {cb_name} data: {filename}")
            
            # Dynamically register the callback with the connection.
            register_method = getattr(self.__connection, config["register_method"])
            # Use a lambda with a default argument to bind the callback name.
            register_method(lambda message, cb=cb_name: self.handle_callback(cb, message))
            
    def handle_callback(self, cb_name, message):
        """
        Generic callback handler: print the message with prefix, parse the data,
        and log it to the appropriate CSV file.
        """
        msg_str = message.to_string()
        print(self.__prefix + msg_str)
        # Use the designated parser for this callback type.
        row = self.callback_configs[cb_name]["parser"](message)
        if row is not None and cb_name in self.csv_writers:
            self.csv_writers[cb_name].writerow(row)
            self.csv_files[cb_name].flush()

    def parse_inertial (self, message):
        
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 4:
            print("Unexpected magnetometer message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        gyro_x , gyro_y, gyro_z = parts[1:4]
        acc_x, acc_y, acc_z = parts[-4:]
        return [device_name, timestamp, gyro_x , gyro_y, gyro_z, acc_x, acc_y, acc_z]


    def parse_magnetometer(self, message):
        """
        Custom parser for magnetometer messages.
        """
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 4:
            print("Unexpected magnetometer message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        mag_x, mag_y, mag_z = parts[1:]
        return [device_name, timestamp, mag_x, mag_y, mag_z]

    def parse_quaternion(self, message):
        """
        Custom parser for quaternion messages.
        Expected format (space separated):
          parts[0] = device name, parts[1] = serial, parts[2] = timestamp,
          parts[3] = unit, parts[4:8] = quaternion values.
        """
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 4:
            print("Unexpected quaternion message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        q0, q1, q2, q3 = parts[-4:]
        return [device_name, timestamp, q0, q1, q2, q3]
    
    def parse_rotation(self, message):
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 4:
            print("Unexpected quaternion message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        R_xx,R_xy, R_xz, R_yx,R_yy,R_yz,R_zx,R_zy,R_zz = parts[-9:]
        return [device_name, timestamp, R_xx,R_xy, R_xz, R_yx,R_yy,R_yz,R_zx,R_zy,R_zz]
    
    def parse_euler(self, message):
        """
        Custom parser for magnetometer messages.
        """
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 3:
            print("Unexpected magnetometer message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        roll, pitch, yaw  = parts[1:]
        return [device_name, timestamp, roll, pitch, yaw]
    
    def parse_linear_acc(self, message):
        
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 3:
            print("Unexpected quaternion message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        q0, q1, q2, q3 = parts[1:5]
        x, y, z = parts[-3:]
        return [device_name, timestamp, q0, q1, q2, q3, x, y, z]    
        
    
    def parse_earth_linear_acc(self, message):
        
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 3:
            print("Unexpected quaternion message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        q0, q1, q2, q3 = parts[1:5]
        x, y, z = parts[-3:]
        return [device_name, timestamp, q0, q1, q2, q3, x, y, z]
        
  
    
    def parse_high_g(self, message): 
        
        data_str = message.to_string()
        parts = data_str.split()
        if len(parts) < 3:
            print("Unexpected quaternion message format:", data_str)
            return None
        device_name = self.__prefix.split()[0]
        timestamp = parts[0]
        x, y, z = parts[-3:]
        return [device_name, timestamp, x, y, z]

    def parse_error(self, message):
        """
        Default parser that returns the complete message string in a list.
        """
        return [message.to_string()]
    
    def __ahrs_status_callback(self, message):
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
    
    

    def close(self):
        self.__connection.close()
        # Close all CSV files.
        for cb_name, csv_file in self.csv_files.items():
            csv_file.close()
            print(f"{cb_name.capitalize()} CSV file closed.")

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

    

connections = [Connection(m.to_udp_connection_info()) for m in ximu3.NetworkAnnouncement().get_messages_after_short_delay()]

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
#csv_file.close()