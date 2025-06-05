# modules/vision.py
import cv2
import os
import subprocess
import time

class VisionModule:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index

    def force_exposure_v4l2(self):
        try:
            # Switch to manual exposure mode (1 = Manual Mode)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=auto_exposure=1"
            ], check=True)

            # Optional: small delay to allow control change to take effect
            time.sleep(0.1)

            # Set absolute exposure time (valid range: 3–2047)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=exposure_time_absolute=500"
            ], check=True)

            # Set brightness (0–127)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=brightness=50"
            ], check=True)

            # Set contrast (0–95)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=contrast=60"
            ], check=True)

            # Set gamma (100–300)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=gamma=150"
            ], check=True)

            # Set backlight compensation (0–255)
            subprocess.run([
                "v4l2-ctl", "-d", f"/dev/video{self.camera_index}",
                "--set-ctrl=backlight_compensation=200"
            ], check=True)

            print("[Vision] Exposure and image parameters tuned via v4l2-ctl.")
        except Exception as e:
            print(f"[Vision] Failed to set manual exposure: {e}")

    def capture_image(self, save_path=None):
        if save_path is None:
            save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../visual/static/latest.jpg"))

        self.force_exposure_v4l2()

        cap = cv2.VideoCapture(self.camera_index)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {self.camera_index}")

        # Optional: more in-frame control, though most are handled via v4l2 now
        cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 0.25 for manual, 0.75 for auto
        cap.set(cv2.CAP_PROP_BACKLIGHT, 1)  # 0–1 range for OpenCV, varies by camera

        ret, frame = cap.read()
        cap.release()

        if not ret:
            raise RuntimeError("Failed to capture image.")

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        if not cv2.imwrite(save_path, frame):
            raise RuntimeError("Failed to save image.")

        print(f"[Vision] Image captured and saved to {save_path}")
        return save_path
