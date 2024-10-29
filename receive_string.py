import socket
import serial

def receive_ip(port=8000):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', port))
        print(f"UDP服务器正在端口 {port} 上等待接收IP地址...")
        data, address = sock.recvfrom(4096)
        ip_address = data.decode('utf-8')
        print(f"接收到来自 {address} 的IP地址: {ip_address}")
        return ip_address

def calculate_parity_byte(data):
    return sum(bin(byte).count('1') for byte in data) % 2

def create_packet_with_parity(data):
    parity_byte = calculate_parity_byte(data)
    return data + bytes([parity_byte])

def calculate_segment(segment):
    result = 0
    for i, char in enumerate(segment):
        if char == '1':
            result |= (1 << (i * 2))
        elif char == '2':
            result |= (2 << (i * 2))
    return result

def start_udp_server(port=8765):
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', port))
        try:
            ser = serial.Serial(port='COM4', baudrate=115200, timeout=1)
            serial_available = True
        except serial.SerialException:
            print("无法打开COM口，串口通信将被跳过。")
            serial_available = False

        print(f"UDP服务器正在端口 {port} 上等待接收数据...")
        head, tail = 0xA5, 0x7B

        while True:
            data, address = sock.recvfrom(4096)
            message = data.decode('utf-8').strip()
            print(f"接收到来自 {address} 的数据: {message}")

            if len(message) == 11 and all(c in '012' for c in message):
                if serial_available:
                    ser.write(bytes([head]))
                    sum1 = calculate_segment(message[:3])  # 前三个元素
                    sum2 = calculate_segment(message[3:6])  # 中间三个元素
                    sum3 = calculate_segment(message[6:9])  # 再中间三个元素
                    sum4 = calculate_segment(message[9:11])  # 最后两个元素
                    packet = create_packet_with_parity(bytes([sum1, sum2, sum3, sum4]))
                    ser.write(packet + bytes([tail]))
                    print(sum1, sum2, sum3, sum4)

if __name__ == '__main__':
    start_udp_server()
