import connection
import helpers
import ximu3
import csv
import time 

if helpers.ask_question("Search for connections?"):
    print("Searching for connections")

    messages = ximu3.NetworkAnnouncement().get_messages_after_short_delay()
    print(messages[0])
    if not messages:
        raise Exception("No UDP connections available")

    print(f"Found {messages[0].device_name} {messages[0].serial_number}")

    connection.run(messages[0].to_udp_connection_info())
else:
    connection.run(ximu3.UdpConnectionInfo("192.168.1.1", 9000, 8000))


with open('imu_log.csv', 'w', newline='') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['timestamp', 'ax', 'ay', 'az', 'gx', 'gy', 'gz', 'mx', 'my', 'mz'])
    
    try:
        while True:
            # Retrieve the latest data from the IMU (the API converts raw values to physical units)
            data = imu.read_data()
            timestamp = time.time()
            
            # Extract sensor values from the returned data structure
            ax, ay, az = data['linear_acceleration']
            gx, gy, gz = data['angular_velocity']
            mx, my, mz = data['magnetometer']
            
            # Log the data into CSV
            csv_writer.writerow([timestamp, ax, ay, az, gx, gy, gz, mx, my, mz])
            
            # Sleep briefly to approximate a 400 Hz update rate
            time.sleep(0.0025)
    except KeyboardInterrupt:
        # Allow graceful termination on Ctrl-C
        pass

# Close the connection once logging is complete
connection.close()