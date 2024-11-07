import cv2
import numpy as np

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 2688)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1520)
cap.set(cv2.CAP_PROP_FPS, 30)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0)
cap.set(cv2.CAP_PROP_EXPOSURE, -6)

has_init = False
# x, y, w, h = 695, 85, 1345, 1345
x, y, w, h = 700, 90, 1335, 1335
d = min(w, h)
r = d / 2.0

map_y, map_x = None, None
while True:
    # 读取图片
    src = cap.read()[1]
    if src is None:
        print("Error: Could not read frame.")
        break

    if not has_init:

        imgRoi = src[y : y + d, x : x + d]

        # 建立映射表
        map_x = np.zeros((imgRoi.shape[0], imgRoi.shape[1]), dtype=np.float32)
        map_y = np.zeros((imgRoi.shape[0], imgRoi.shape[1]), dtype=np.float32)

        for j in range(d - 1):
            for i in range(d - 1):
                # map_x[i, j] = d / 2.0 + i / 2.0 * np.cos(1.0 * j / d * 2 * np.pi)
                # map_y[i, j] = d / 2.0 + i / 2.0 * np.sin(1.0 * j / d * 2 * np.pi)
                map_x[i, j] = (j - r) / r * (r**2 - (i - r) ** 2) ** 0.5 + r
                map_y[i, j] = i

        has_init = True

    imgRoi = src[y : y + d, x : x + d]
    imgRoi = cv2.flip(imgRoi, 1)
    cv2.imshow("imgRoi", imgRoi)

    dst = np.full(imgRoi.shape, 255, dtype=np.uint8)

    dst = cv2.remap(
        imgRoi,
        map_x,
        map_y,
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0),
    )

    # 重设大小
    # dst = cv2.resize(dst, (dst.shape[1] * 2, dst.shape[0] * 1))

    cv2.imshow("dst", dst)

    if cv2.waitKey(1) == ord("q"):
        break
    
