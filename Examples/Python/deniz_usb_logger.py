import time
import ximu3
import os

def main():
    # 1. Discover all USB devices
    devices = ximu3.PortScanner.scan_filter(ximu3.CONNECTION_TYPE_USB)
    if not devices:
        raise Exception("No xIMU3 devices found over USB.")

    # 2. Open connections
    connections = []
    for device in devices:
        print("Discovered device:", device.to_string())
        conn = ximu3.Connection(device.connection_info)
        if conn.open() == ximu3.RESULT_OK:
            connections.append(conn)
        else:
            raise Exception(f"Unable to open connection to {device.to_string()}")

    # 3. Log data to CSV for 5 seconds
    destination_folder = "LoggedData"
    session_name = "MyDataSession"
    duration_seconds = 5

    print(f"Logging data for {duration_seconds} seconds...")
    result = ximu3.DataLogger.log(destination_folder, session_name, connections, duration_seconds)

    # The line below simply prints whether DataLogger succeeded (RESULT_OK, etc.)
    print("Logging result:", ximu3.result_to_string(result))

    # 4. Close connections
    for conn in connections:
        conn.close()
    print("All connections closed.")

    # Check the folder structure to see your CSV files:
    #   LoggedData/
    #       MyDataSession/
    #         └ Device12345/
    #             ├─ Inertial.csv
    #             ├─ Magnetometer.csv
    #             ├─ ... etc.

if __name__ == "__main__":
    main()
