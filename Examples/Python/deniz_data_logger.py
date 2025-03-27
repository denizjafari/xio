import time
import ximu3
import threading
from pynput import keyboard
import pandas as pd

class Connection:
    def __init__(self, connection_info):
        self.__connection = ximu3.Connection(connection_info)

        if self.__connection.open() != ximu3.RESULT_OK:
            raise Exception(f"Unable to open {connection_info.to_string()}")

        ping_response = self.__connection.ping()  # send ping so that device starts sending to computer's IP address

        if ping_response.result != ximu3.RESULT_OK:
            raise Exception(f"Ping failed for {connection_info.to_string()}")

        self.__prefix = f"{ping_response.device_name} {ping_response.serial_number} "
        
        # Initialize a list to hold data rows (could also use a shared global list)
        self.data = []

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
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "inertial",
            "gyroX_deg_s": message.gyroX,
            "gyroY_deg_s": message.gyroY,
            "gyroZ_deg_s": message.gyroZ,
            "accX_g": message.accX,
            "accY_g": message.accY,
            "accZ_g": message.accZ
        }
        self.data.append(row)

    def __magnetometer_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "magnetometer",
            "magX_au": message.magX,
            "magY_au": message.magY,
            "magZ_au": message.magZ
        }
        self.data.append(row)

    def __quaternion_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "quaternion",
            "q0": message.q0,
            "q1": message.q1,
            "q2": message.q2,
            "q3": message.q3
        }
        self.data.append(row)

    def __rotation_matrix_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "rotation_matrix",
            "R11": message.R11,
            "R12": message.R12,
            "R13": message.R13,
            "R21": message.R21,
            "R22": message.R22,
            "R23": message.R23,
            "R31": message.R31,
            "R32": message.R32,
            "R33": message.R33
        }
        self.data.append(row)

    def __euler_angles_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "euler_angles",
            "roll_deg": message.roll,
            "pitch_deg": message.pitch,
            "yaw_deg": message.yaw
        }
        self.data.append(row)

    def __linear_acceleration_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "linear_acceleration",
            "linAccX_g": message.linAccX,
            "linAccY_g": message.linAccY,
            "linAccZ_g": message.linAccZ
        }
        self.data.append(row)

    def __earth_acceleration_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "earth_acceleration",
            "earthAccX_g": message.earthAccX,
            "earthAccY_g": message.earthAccY,
            "earthAccZ_g": message.earthAccZ
        }
        self.data.append(row)

    def __ahrs_status_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "ahrs_status",
            "initialising": bool(message.initialising),
            "angular_rate_recovery": bool(message.angularRateRecovery),
            "acceleration_recovery": bool(message.accelerationRecovery),
            "magnetic_recovery": bool(message.magneticRecovery)
        }
        self.data.append(row)

    def __high_g_accelerometer_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "high_g_accelerometer",
            "hgAccX_g": message.hgAccX,
            "hgAccY_g": message.hgAccY,
            "hgAccZ_g": message.hgAccZ
        }
        self.data.append(row)

    def __temperature_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "temperature",
            "temperature_C": message.value
        }
        self.data.append(row)

    def __battery_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "battery",
            "battery_%": message.battery_level,
            "voltage_V": message.voltage,
            "charging_status": message.charging_status  # 0:Not connected,1:Charging,2:Complete
        }
        self.data.append(row)

    def __rssi_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "rssi",
            "rssi_%": message.rssi_percentage,
            "rssi_dBm": message.rssi_dBm
        }
        self.data.append(row)

    def __serial_accessory_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "serial_accessory",
            "data": message.data
        }
        self.data.append(row)

    def __notification_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "notification",
            "notification": message.description
        }
        self.data.append(row)

    def __error_callback(self, message):
        print(self.__prefix + message.to_string())
        row = {
            "timestamp": message.timestamp,
            "sensor": self.__prefix,
            "message_type": "error",
            "error_description": message.description
        }
        self.data.append(row)

def on_press(key, stop_event):
    """Callback function to handle key press events."""
    try:
        if key.char == 'q':
            print("Stopping connections...")
            stop_event.set()
            return False  # Stop listener
    except AttributeError:
        pass

def monitor_key_press(stop_event):
    """Monitors for a specific key press to set the stop event."""
    with keyboard.Listener(on_press=lambda key: on_press(key, stop_event)) as listener:
        listener.join()

if __name__ == "__main__":
    connections = [Connection(m.to_udp_connection_info()) for m in ximu3.NetworkAnnouncement().get_messages_after_short_delay()]

    if not connections:
        raise Exception("No UDP connections available")


    
    stop_event = threading.Event()
    key_monitor_thread = threading.Thread(target=monitor_key_press, args=(stop_event,))
    key_monitor_thread.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()

    key_monitor_thread.join()

    for connection in connections:
        connection.send_command('shutdown')
        time.sleep(0.5)  # Optional: wait for a second before sending the next command

    # Gather data from all connections and close
    all_data_rows = []
    for connection in connections:
        all_data_rows.extend(connection.data)
        connection.close()


    # Convert accumulated data into a DataFrame
    df = pd.DataFrame(all_data_rows)

    # Write the DataFrame to CSV
    df.to_csv("./Data/output_data.csv", index=False)
    print("Data successfully written to output_data.csv")