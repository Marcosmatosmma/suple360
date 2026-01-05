import cv2
import time
import threading
from utils import draw_overlays


class Detector:
    """Gerencia detecção YOLO com fusão de dados LIDAR"""
    
    def __init__(self, model, db_manager, lidar_manager, camera_manager, screenshot_dir, cam_hfov_deg=70.0):
        self.model = model
        self.db_manager = db_manager
        self.lidar_manager = lidar_manager
        self.camera_manager = camera_manager
        self.screenshot_dir = screenshot_dir
        self.cam_hfov_deg = cam_hfov_deg
        self.detection_counter = 0
    
    def detection_loop(self):
        """Loop de detecção contínua"""
        while True:
            frame = self.camera_manager.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            target_w, target_h = 640, 360
            det_input = cv2.resize(frame, (target_w, target_h))
            results = self.model(det_input)
            
            scale_x = frame.shape[1] / target_w
            scale_y = frame.shape[0] / target_h
            new_boxes = []
            frame_w = frame.shape[1]
            
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    x1 = int(x1 * scale_x)
                    x2 = int(x2 * scale_x)
                    y1 = int(y1 * scale_y)
                    y2 = int(y2 * scale_y)
                    conf = float(box.conf[0])
                    
                    x_center = (x1 + x2) / 2.0
                    rel = (x_center / frame_w) - 0.5
                    angle_deg = rel * self.cam_hfov_deg
                    dist_m = self.lidar_manager.sector_to_distance(angle_deg)
                    
                    width_m = None
                    if dist_m is not None:
                        box_ang = ((x2 - x1) / frame_w) * self.cam_hfov_deg
                        width_m = max(0.0, dist_m * 2 * 3.14159 * (box_ang / 360.0))
                    
                    new_boxes.append((x1, y1, x2, y2, conf, dist_m, width_m))
            
            if new_boxes:
                self.detection_counter += 1
                text = f"✓ BURACO DETECTADO! ({len(new_boxes)} objeto(s))"
                color = (0, 0, 255)
                
                annotated = draw_overlays(frame.copy(), new_boxes, text, color)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                filename = f"buraco_{time.strftime('%Y%m%d_%H%M%S')}_{self.detection_counter}.jpg"
                full_path = f"{self.screenshot_dir}/{filename}"
                cv2.imwrite(full_path, annotated)
                print(f"✓ Buraco detectado! Foto {self.detection_counter} salva: {full_path}")
                
                self.db_manager.add_detection(
                    photo_path=filename,
                    boxes=new_boxes,
                    timestamp=timestamp
                )
            else:
                text = "Nenhum buraco detectado"
                color = (0, 255, 0)
            
            self.camera_manager.update_detections(new_boxes, text, color)
    
    def start(self):
        """Inicia thread de detecção"""
        threading.Thread(target=self.detection_loop, daemon=True).start()
        print("Thread de detecção iniciada")
