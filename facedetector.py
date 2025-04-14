import cv2
import mediapipe as mp
import time
import webbrowser
import sqlite3
import os
from datetime import datetime

def save_face_image(frame):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    image_path = f"faces/face_{timestamp}.jpg"
    os.makedirs("faces", exist_ok=True)
    cv2.imwrite(image_path, frame)
    
    phone_path = f"/sdcard/DCIM/face_{timestamp}.jpg"  # Android path
    os.system(f"adb push {image_path} {phone_path}")
    
 
    
    return image_path

conn = sqlite3.connect('timer_data.db')
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS timer_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    elapsed_time REAL,
    face_image_path TEXT
)
''')
conn.commit()

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True, min_detection_confidence=0.5)
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1)
mp_drawing = mp.solutions.drawing_utils

start_time = 0
elapsed_time = 0
timer_running = False
manual_control = False
data_saved = False
face_detected = False
last_face_time = 0
warning_displayed = False

button_pos = (30, 120)
button_size = (120, 40)
button_clicked = False

cv2.namedWindow("MediaPipe Timer")

def click_event(event, x, y, flags, param):
    global button_clicked
    if event == cv2.EVENT_LBUTTONDOWN:
        bx, by = button_pos
        bw, bh = button_size
        if bx <= x <= bx + bw and by <= y <= by + bh:
            button_clicked = True
            webbrowser.open("http://localhost:5173/")

cv2.setMouseCallback("MediaPipe Timer", click_event)

def fingers_up(hand_landmarks):
    finger_tips = [8, 12, 16, 20]  
    finger_status = []
    for tip_id in finger_tips:
        tip = hand_landmarks.landmark[tip_id]
        pip = hand_landmarks.landmark[tip_id - 2]
        finger_status.append(tip.y < pip.y)
    return finger_status

cap = cv2.VideoCapture(0)
face_timeout = 1.0  

while True:
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    frame = cv2.flip(frame, 1)
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    
    face_result = face_mesh.process(rgb)
    hand_result = hands.process(rgb)

    
    if not manual_control:
        current_face_detected = face_result.multi_face_landmarks is not None

        if current_face_detected:
            last_face_time = time.time()
            warning_displayed = False
            if not timer_running:
               
                start_time = time.time() - elapsed_time
                timer_running = True
                face_detected = True
                data_saved = False
                print("Face detected - Timer started")
        else:
            
            if not warning_displayed:
                warning_displayed = True
                print("Warning: Face not detected!")
            
            
            if timer_running and (time.time() - last_face_time) > face_timeout:
                elapsed_time = time.time() - start_time
                timer_running = False
                face_detected = False
                print("Face lost - Timer stopped")

    else:
        face_detected = False
        warning_displayed = False

    if hand_result.multi_hand_landmarks:
        hand_landmarks = hand_result.multi_hand_landmarks[0]
        finger_states = fingers_up(hand_landmarks)
        raised_fingers = sum(finger_states)

        if raised_fingers == 2 and finger_states[0] and finger_states[1]:
            manual_control = True
            if timer_running:
                elapsed_time = time.time() - start_time
                timer_running = False
                print("Manual stop - Timer stopped")

        elif raised_fingers == 3 and finger_states[0] and finger_states[1] and finger_states[2]:
            manual_control = True
            if not timer_running:
                start_time = time.time() - elapsed_time
                timer_running = True
                data_saved = False
                print("Manual start - Timer started")

        elif raised_fingers != 2 and raised_fingers != 3:
            manual_control = False

        if finger_states[0] and not any(finger_states[1:]):
            index_tip = hand_landmarks.landmark[8]
            x = int(index_tip.x * w)
            y = int(index_tip.y * h)
            bx, by = button_pos
            bw, bh = button_size
            if bx <= x <= bx + bw and by <= y <= by + bh and not button_clicked:
                button_clicked = True
                webbrowser.open("http://localhost:5173/")

    current_time = time.time() - start_time if timer_running else elapsed_time
    milliseconds = int((current_time - int(current_time)) * 1000)
    total_seconds = int(current_time)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    timer_text = f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"

    status_text = "Timer Running" if timer_running else "Timer Stopped"
    control_mode = " (Manual)" if manual_control else " (Auto)"
    status_color = (0, 255, 0) if timer_running else (0, 0, 255)
    cv2.putText(frame, status_text + control_mode, (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, status_color, 2)
    cv2.putText(frame, timer_text, (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    if not manual_control and not face_result.multi_face_landmarks:
        warning_text = "Warning: Face not detected!"
        cv2.putText(frame, warning_text, (w//2 - 200, h - 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    bx, by = button_pos
    bw, bh = button_size
    cv2.rectangle(frame, button_pos, (bx + bw, by + bh), (0, 255, 0), -1)
    cv2.putText(frame, "Click Here", (bx + 5, by + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    if not timer_running and not data_saved and elapsed_time > 0:
        image_path = save_face_image(frame)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("INSERT INTO timer_logs (timestamp, elapsed_time, face_image_path) VALUES (?, ?, ?)",
                      (timestamp, elapsed_time, image_path))
        conn.commit()
        print(f"Data saved: {elapsed_time:.2f} seconds {'(manual stop)' if manual_control else '(auto stop)'}")
        data_saved = True

    cv2.imshow("MediaPipe Timer", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()
conn.close()