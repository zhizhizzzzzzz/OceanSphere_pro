import numpy as np
import cv2
from socket import *
from receive_string import receive_ip

# 接收目标IP地址
target_ip = receive_ip()
addr = (target_ip, 8081)

cap = cv2.VideoCapture(0)
# 设置镜头分辨率，默认是640x480
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
s = socket(AF_INET, SOCK_DGRAM) # 创建UDP套接字

while True:
    _, img = cap.read()
    img = cv2.flip(img, 1)
    # 压缩图片
    _, send_data = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 50])
    s.sendto(send_data, addr)
    print(f'正在向{addr}发送数据，大小:{img.size} Byte')
    cv2.putText(img, "client", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.imshow('client', img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

s.close()
cv2.destroyAllWindows()
