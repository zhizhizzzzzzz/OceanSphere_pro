import numpy as np
import cv2
import socket
import serial
import threading
import time

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

def send_video_frames(target_ip):
    addr = (target_ip, 8081)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    start_time = time.time()

    while True:
        ret, img = cap.read()
        if not ret:
            break
        img = cv2.flip(img, 1)
        _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
        s.sendto(send_data, addr)
        
        current_time = time.time()
        if current_time - start_time >= 10:
            print(f'正在向{addr}发送数据，大小:{img.size} Byte')
            start_time = current_time
            
        cv2.putText(img, "client", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow('client', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    s.close()
    cap.release()
    cv2.destroyAllWindows()

def main():
    target_ip = receive_ip()
    udp_thread = threading.Thread(target=start_udp_server)
    video_thread = threading.Thread(target=send_video_frames, args=(target_ip,))
    
    udp_thread.start()
    video_thread.start()
    
    udp_thread.join()
    video_thread.join()

if __name__ == '__main__':
    main()
