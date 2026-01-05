import cv2
import threading
from utils import draw_overlays


class CameraManager:
    """Gerencia captura de frames da câmera"""
    
    def __init__(self, camera):
        self.camera = camera
        self.frame_global = None
        self.latest_frame = None
        self.detection_boxes = []
        self.detection_text = "Inicializando..."
        self.detection_color = (0, 255, 0)
        self.lock = threading.Lock()
        self.frame_count = 0
    
    def get_latest_frame(self):
        """Retorna cópia do último frame capturado"""
        with self.lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()
    
    def get_stream_frame(self):
        """Retorna frame com overlay para streaming"""
        with self.lock:
            return self.frame_global
    
    def update_detections(self, boxes, text, color):
        """Atualiza detecções para overlay"""
        with self.lock:
            self.detection_boxes = boxes
            self.detection_text = text
            self.detection_color = color
    
    def capture_loop(self):
        """Loop de captura contínua de frames"""
        while True:
            frame = self.camera.capture_array()
            
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            self.frame_count += 1
            
            with self.lock:
                self.latest_frame = frame.copy()
                boxes = self.detection_boxes.copy()
                text = self.detection_text
                color = self.detection_color
            
            frame_vis = draw_overlays(frame.copy(), boxes, text, color, frame_id=self.frame_count)
            
            with self.lock:
                self.frame_global = frame_vis
    
    def start(self):
        """Inicia thread de captura"""
        threading.Thread(target=self.capture_loop, daemon=True).start()
        print("Thread de captura iniciada")
