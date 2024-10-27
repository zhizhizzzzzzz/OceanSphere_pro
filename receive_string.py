import socket
import serial

def calculate_parity_byte(data):
    # 计算数据中1的个数
    ones_count = sum(bin(byte).count('1') for byte in data)
    
    # 如果1的个数是奇数，返回1；否则返回0
    return 1 if ones_count % 2 else 0

def create_packet_with_parity(data):
    # 计算奇偶校验位
    parity_byte = calculate_parity_byte(data)
    
    # 将数据包和奇偶校验位打包在一起
    packet = data + bytes([parity_byte])
    return packet

def start_udp_server(port=8765):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('', port)
    sock.bind(server_address)

    try:
        ser = serial.Serial(
            port='COM3',  # win写COM3，Ubuntu写/dev/ttyUSB0
            baudrate=115200,
            timeout=1
        )
        serial_available = True
    except serial.SerialException:
        print("无法打开COM口，串口通信将被跳过。")
        serial_available = False

    print(f"UDP服务器正在端口 {port} 上等待接收数据...")

    head = 0xA5
    tail = 0x7B
    try:
        while True:
            data, address = sock.recvfrom(4096)
            if data:
                message = data.decode('utf-8')
                print(f"接收到来自 {address} 的数据: {message}")
                
                # 串口可用时才发送数据
                if serial_available:
                    ser.write(bytes([head]))
                    sum = 0
                    for i, char in enumerate(message):
                        if int(char) == 1:
                            sum += 1 << (2 * i)
                        elif int(char) == 2:
                            sum += 2 << (2 * i)
                    
                    packet = create_packet_with_parity(sum.to_bytes(1, byteorder="big"))
                    ser.write(packet)
                    print(sum)
                    ser.write(bytes([tail]))

    except KeyboardInterrupt:
        print("服务器已停止")
    finally:
        sock.close()
        if serial_available:
            ser.close()

if __name__ == '__main__':
    start_udp_server()
