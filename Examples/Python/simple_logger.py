import csv
import connection
import helpers
import ximu3


data_rows = []
headers = ['Timestamp', 'SensorID','GyroX', 'GyroY', 'GyroZ', 'AccX', 'AccY', 'AccZ']
data_rows.append(headers)



def inertial_callback(message):
    row = [
        message.timestamp,
        message.gyroX,
        message.gyroY,
        message.gyroZ,
        message.accX,
        message.accY,
        message.accZ
    ]
    data_rows.append(row)




def run(connection_info, callback):
    conn = ximu3.Connection(connection_info)
    if conn.open() != ximu3.RESULT_OK:
        raise Exception("Unable to open connection")

    conn.add_inertial_callback(callback)

    # Existing code to handle connection...

    conn.close()


if __name__ == "__main__":
    if helpers.ask_question("Search for connections?"):
        messages = ximu3.NetworkAnnouncement().get_messages_after_short_delay()
        if not messages:
            raise Exception("No UDP connections available")
        connection.run(messages[0].to_udp_connection_info(), inertial_callback)
    else:
        connection.run(ximu3.UdpConnectionInfo("192.168.1.1", 9000, 8000), inertial_callback)

    # After data collection, write to CSV
    with open('imu_data.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(data_rows)
