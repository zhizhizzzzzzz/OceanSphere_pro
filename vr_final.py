import numpy as np
import cv2
import socket
import serial
import threading
import time

cap1 = None
cap2 = None
button_pressed = False

def initialize_cameras():
    global cap1, cap2
    cap1 = cv2.VideoCapture(1)
    cap2 = cv2.VideoCapture(2)
    if not cap1.isOpened() or not cap2.isOpened():
        print("Error: Could not open camera(s).")
        return None, None

    cap1.set(cv2.CAP_PROP_FRAME_WIDTH, 2688)
    cap1.set(cv2.CAP_PROP_FRAME_HEIGHT, 1520)
    cap1.set(cv2.CAP_PROP_FPS, 30)
    cap1.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
    cap1.set(cv2.CAP_PROP_EXPOSURE, -6)

    cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 2688)
    cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 1520)
    cap2.set(cv2.CAP_PROP_FPS, 30)
    cap2.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
    cap2.set(cv2.CAP_PROP_EXPOSURE, -6)

    return cap1, cap2

def initialize_remap_maps(d, r):
    map_y1, map_x1 = np.zeros((d, d), dtype=np.float32), np.zeros((d, d), dtype=np.float32)
    map_y2, map_x2 = np.zeros((d, d), dtype=np.float32), np.zeros((d, d), dtype=np.float32)
    for j in range(d - 1):
        for i in range(d - 1):
            map_x1[i, j] = (j - r) / r * (r ** 2 - (i - r) ** 2)**0.5 + r
            map_y1[i, j] = i
            map_x2[i, j] = (j - r) / r * (r ** 2 - (i - r) ** 2)**0.5 + r
            map_y2[i, j] = i
    return map_x1, map_y1, map_x2, map_y2

def get_merged_img(cap1, cap2, map_x1, map_y1, map_x2, map_y2):
    x1, x2, y, w, h = 698, 649, 85, 1345, 1345
    d = min(w, h)

    ret1, frame1 = cap1.read()
    ret2, frame2 = cap2.read()

    if not ret1 or not ret2:
        print("Error: Could not read frame(s).")
        return None

    imgRoi1 = frame1[y: y + d, x1: x1 + d]
    imgRoi1 = cv2.flip(imgRoi1, 1)

    imgRoi2 = frame2[y: y + d, x2: x2 + d]
    imgRoi2 = cv2.flip(imgRoi2, 1)

    dst1 = cv2.remap(
        imgRoi1,
        map_x1,
        map_y1,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    dst2 = cv2.remap(
        imgRoi2,
        map_x2,
        map_y2,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0)
    )

    # 拼接图像
    merged_image = cv2.hconcat([dst1, dst2])
    resized_image = cv2.resize(merged_image, (760, 380), interpolation=cv2.INTER_AREA)  # 调整显示窗口的大小
    return resized_image
        
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
    global button_pressed, last_pressed_time  # 使用全局变量来保存按钮状态和上次按下时间

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('', port))
        try:
            ser = serial.Serial(port='/dev/ttyUSB0', baudrate=115200, timeout=1)
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
            
            # 如果接收到的是按钮按下信号
            if message == "00000020000" and not button_pressed:  # 按下按钮且未处理过
                print("Button '00000020000' pressed. Swapping cameras.")
                swap_cameras()  # 交换摄像头
                button_pressed = True  # 设置按钮状态为按下
                last_pressed_time = time.time()  # 记录按下时间

            # 如果接收到的是按钮松开信号
            elif message == "00000000000" and button_pressed:  # 松开按钮且之前按下
                print("Button released. No action.")
                button_pressed = False  # 设置按钮状态为松开

            # 防止长按导致重复交换摄像头
            elif message == "00000020000" and button_pressed:
                current_time = time.time()
                # 如果短时间内多次接收到 '00000020000'，则忽略
                if current_time - last_pressed_time < 1:  # 设置防抖时间阈值（比如0.5秒）
                    continue
                last_pressed_time = current_time  # 更新上次按下的时间

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
                    
def swap_cameras():
    global button_pressed
    
    button_pressed = True
    print("change OK")

def send_video_frames(target_ip):
    global button_pressed
    start_time = time.time()

    addr = (target_ip, 8081)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cap1, cap2 = initialize_cameras()
    x1, x2, y, w, h = 649, 698, 85, 1345, 1345
    d = min(w, h)
    r = d / 2.0
    map_x1, map_y1, map_x2, map_y2 = initialize_remap_maps(d, r)
    
    while True:
        
        merged_image = get_merged_img(cap1, cap2, map_x1, map_y1, map_x2, map_y2)
        
        if merged_image is None:
            print("Error: Merged image is empty. Skipping frame.")
            continue  # 跳过空帧
        
        # print("****************",merged_image.size,"*******************")
        img = cv2.flip(merged_image, 1)
        _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        s.sendto(send_data, addr)
        
        current_time = time.time()
        if current_time - start_time >= 10:
            print(f'正在向{addr}发送数据，大小:{len(send_data)} Byte')
            start_time = current_time
            
        cv2.putText(img, "client", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
        cv2.imshow('client', img)
        
        if button_pressed:
            t = cap1
            cap1 = cap2
            cap2 = t
            button_pressed = False
            
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    s.close()
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
