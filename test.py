import numpy as np
import cv2

h = 500
w = 500
img = 255 * np.ones((h ,w , 3), dtype=np.uint8)
cv2.imshow("", img)
cv2.waitKey(0)