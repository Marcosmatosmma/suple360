import cv2
import time
import threading
from utils import draw_overlays
from opencv_analyzer import OpenCVAnalyzer
from tracker import BuracoTracker


class Detector:
    """Gerencia detecção YOLO com fusão de dados LIDAR, análise OpenCV e tracking"""
    
    def __init__(self, model, db_manager, lidar_manager, camera_manager, screenshot_dir, cam_hfov_deg=70.0):
        self.model = model
        self.db_manager = db_manager
        self.lidar_manager = lidar_manager
        self.camera_manager = camera_manager
        self.screenshot_dir = screenshot_dir
        self.cam_hfov_deg = cam_hfov_deg
        self.detection_counter = 0
        
        # Novos módulos da Fase 1
        self.opencv_analyzer = OpenCVAnalyzer()
        self.tracker = BuracoTracker(iou_threshold=0.3, max_age_seconds=5.0)
    
    def detection_loop(self):
        """Loop de detecção contínua com análise OpenCV e tracking"""
        while True:
            frame = self.camera_manager.get_latest_frame()
            if frame is None:
                time.sleep(0.01)
                continue
            
            # Detecção YOLO em resolução reduzida
            target_w, target_h = 640, 360
            det_input = cv2.resize(frame, (target_w, target_h))
            results = self.model(det_input)
            
            # Escala boxes de volta para resolução original
            scale_x = frame.shape[1] / target_w
            scale_y = frame.shape[0] / target_h
            detections = []
            frame_w = frame.shape[1]
            
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(float, box.xyxy[0])
                    x1 = int(x1 * scale_x)
                    x2 = int(x2 * scale_x)
                    y1 = int(y1 * scale_y)
                    y2 = int(y2 * scale_y)
                    conf = float(box.conf[0])
                    
                    # Calcula ângulo e distância com LIDAR
                    x_center = (x1 + x2) / 2.0
                    rel = (x_center / frame_w) - 0.5
                    angle_deg = rel * self.cam_hfov_deg
                    dist_m = self.lidar_manager.sector_to_distance(angle_deg)
                    
                    # Calcula largura usando LIDAR
                    width_m = None
                    if dist_m is not None:
                        box_ang = ((x2 - x1) / frame_w) * self.cam_hfov_deg
                        width_m = max(0.0, dist_m * 2 * 3.14159 * (box_ang / 360.0))
                    
                    detections.append((x1, y1, x2, y2, conf, dist_m, width_m))
            
            # Atualiza tracker e identifica novos buracos
            novos_buracos, buracos_atualizados = self.tracker.update(detections)
            
            # Processa apenas NOVOS buracos (evita duplicatas)
            if novos_buracos:
                self.detection_counter += 1
                text = f"✓ NOVO BURACO! (Total: {len(novos_buracos)})"
                color = (0, 0, 255)
                
                # Analisa cada novo buraco com OpenCV
                analysis_data = []
                for buraco_info in novos_buracos:
                    detection = buraco_info['detection']
                    track_id = buraco_info['track_id']
                    
                    bbox = detection[:4]
                    dist_m = detection[5] if len(detection) > 5 else None
                    
                    # Análise OpenCV
                    analysis = self.opencv_analyzer.analisar_buraco(frame, bbox, dist_m)
                    analysis['track_id'] = track_id
                    analysis_data.append(analysis)
                
                # Salva frame anotado
                all_boxes = [b['detection'] for b in novos_buracos]
                annotated = draw_overlays(frame.copy(), all_boxes, text, color)
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                filename = f"buraco_{time.strftime('%Y%m%d_%H%M%S')}_{self.detection_counter}.jpg"
                full_path = f"{self.screenshot_dir}/{filename}"
                cv2.imwrite(full_path, annotated)
                
                # Log detalhado
                print(f"\n{'='*60}")
                print(f"✓ NOVO BURACO DETECTADO! Foto {self.detection_counter}")
                print(f"{'='*60}")
                for idx, analysis in enumerate(analysis_data):
                    print(f"\nBuraco #{idx+1} (Track ID: {analysis['track_id']}):")
                    dims = analysis['dimensoes_reais']
                    if dims['area_m2']:
                        print(f"  Área: {dims['area_m2']:.4f} m²")
                        print(f"  Dimensões: {dims['largura_m']:.2f}m x {dims['altura_m']:.2f}m")
                        print(f"  Circularidade: {analysis['geometria']['circularidade']:.2f}")
                        print(f"  Severidade: {analysis['classificacao']['severidade'].upper()}")
                print(f"{'='*60}\n")
                
                # Salva no banco com dados completos
                self.db_manager.add_detection(
                    photo_path=filename,
                    boxes=all_boxes,
                    timestamp=timestamp,
                    analysis_data=analysis_data
                )
            elif buracos_atualizados:
                # Buracos já conhecidos (apenas atualiza display)
                text = f"Rastreando {len(buracos_atualizados)} buraco(s)"
                color = (255, 165, 0)  # Laranja
            else:
                text = "Nenhum buraco detectado"
                color = (0, 255, 0)
            
            # Atualiza display com todas as detecções (novas + rastreadas)
            all_current = novos_buracos + buracos_atualizados
            display_boxes = [b['detection'] for b in all_current]
            self.camera_manager.update_detections(display_boxes, text, color)
    
    def start(self):
        """Inicia thread de detecção"""
        threading.Thread(target=self.detection_loop, daemon=True).start()
        print("✓ Thread de detecção iniciada (com OpenCV Analyzer + Tracker)")

