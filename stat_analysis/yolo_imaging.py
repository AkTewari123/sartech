#!/usr/bin/env python3
"""
yolo_pid_distance_safe.py
Adds a safety override:
  -> If the person fills ≥95% of the frame height,
     force the drone to move backward.
"""

import time
import math
import cv2
import numpy as np
from ultralytics import YOLO


class PID:
    def __init__(self, kp=0.02, ki=0.0, kd=0.003):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.prev_err = 0.0
        self.integral = 0.0

    def compute(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_err) / dt if dt > 0 else 0.0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_err = error
        return output


def draw_text(img, text, pos=(20, 60), scale=1.2, color=(0, 255, 255)):
    font = cv2.FONT_HERSHEY_DUPLEX
    cv2.putText(img, text, pos, font, scale, (0, 0, 0), 4, cv2.LINE_AA)  # outline
    cv2.putText(img, text, pos, font, scale, color, 2, cv2.LINE_AA)      # fill


def main():
    model = YOLO("yolov8n.pt")   # small fast model
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        raise RuntimeError("Cannot open camera.")

    pid_x = PID(kp=0.025, kd=0.004)   # left-right
    pid_y = PID(kp=0.025, kd=0.004)   # up-down
    pid_z = PID(kp=0.02,  kd=0.003)   # forward-back

    target_ratio = 0.8    # Desired height ratio
    emergency_ratio = 0.95  # Safety threshold

    last_time = time.time()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        now = time.time()
        dt = now - last_time
        last_time = now
        h, w = frame.shape[:2]
        cx, cy = w / 2, h / 2

        results = model(frame, imgsz=640, conf=0.35, verbose=False)
        r = results[0]

        vx = vy = vz = 0.0
        angle_deg = 0.0
        commands = "No human detected"

        if hasattr(r, "boxes") and r.boxes is not None and len(r.boxes) > 0:
            xyxy = r.boxes.xyxy.cpu().numpy()
            cls = r.boxes.cls.cpu().numpy().astype(int)
            confs = r.boxes.conf.cpu().numpy()

            best_idx = None
            best_conf = 0
            for i, c in enumerate(cls):
                if c == 0 and confs[i] > best_conf:  # class 0 is 'person'
                    best_idx = i
                    best_conf = confs[i]

            if best_idx is not None:
                x1, y1, x2, y2 = xyxy[best_idx]
                box_cx = (x1 + x2) / 2
                box_cy = (y1 + y2) / 2
                box_h = y2 - y1

                # Draw visuals
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 3)
                cv2.circle(frame, (int(box_cx), int(box_cy)), 6, (0, 255, 255), -1)
                cv2.circle(frame, (int(cx), int(cy)), 7, (0, 0, 255), -1)

                # Errors
                error_x = cx - box_cx
                error_y = cy - box_cy
                size_ratio = box_h / h
                error_z = target_ratio - size_ratio

                # PID outputs
                vx = pid_x.compute(error_x, dt)
                vy = pid_y.compute(error_y, dt)
                vz = pid_z.compute(error_z, dt)

                # Emergency override if person is too close
                if size_ratio >= emergency_ratio:
                    vz = -0.5  # strong backward command

                # Angle of target
                dx = box_cx - cx
                dy = cy - box_cy
                angle_rad = math.atan2(dx, dy + 1e-6)
                angle_deg = math.degrees(angle_rad)

                # Direction helper
                def direction(val, pos_str, neg_str):
                    if abs(val) < 0.02:
                        return "HOLD"
                    return pos_str if val > 0 else neg_str

                left_right = direction(vx, "LEFT", "RIGHT")
                # up_down = direction(vy, "UP", "DOWN")
                # fwd_back = direction(vz, "FORWARD", "BACKWARD")

                # Build command string
                commands = (
                    f"Move {left_right} ({abs(vx):.2f}) | "
                    # f"Move {up_down} ({abs(vy):.2f}) | "
                    # f"Move {fwd_back} ({abs(vz):.2f}) | "
                    # f"Angle: {angle_deg:.1f}° | "
                    # f"Height Ratio: {size_ratio:.2f}"
                )

        print(commands)
        draw_text(frame, commands, pos=(20, 60))

        cv2.imshow("YOLO PID Drone (Safe Distance)", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
