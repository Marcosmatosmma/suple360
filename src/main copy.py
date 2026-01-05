import picamera2
import time
from ultralytics import YOLO
import cv2
import os
from flask import Flask, Response, render_template, jsonify, send_file
import threading
import json
import sqlite3
from datetime import datetime

# Tentativa de importar RPLIDAR; se não disponível, avisamos em runtime
try:
    from rplidar import RPLidar
    HAS_RPLIDAR = True
except ImportError:
    HAS_RPLIDAR = False

class DatabaseManager:
    """Gerencia banco de dados SQLite para detecções"""
    def __init__(self, db_path="deteccoes/detections.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Cria tabelas se não existirem"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabela de detecções
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                num_buracos INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de buracos individuais
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buracos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER NOT NULL,
                bbox_x1 INTEGER,
                bbox_y1 INTEGER,
                bbox_x2 INTEGER,
                bbox_y2 INTEGER,
                confianca REAL,
                distancia_m REAL,
                largura_m REAL,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_detection(self, photo_path, boxes, timestamp):
        """Adiciona detecção e seus buracos ao banco"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Insere detecção principal
                cursor.execute(
                    'INSERT INTO detections (timestamp, photo_path, num_buracos) VALUES (?, ?, ?)',
                    (timestamp, photo_path, len(boxes))
                )
                detection_id = cursor.lastrowid
                
                # Insere cada buraco
                for box in boxes:
                    if len(box) == 7:
                        x1, y1, x2, y2, conf, dist_m, width_m = box
                    else:
                        x1, y1, x2, y2, conf = box[:5]
                        dist_m, width_m = None, None
                    
                    cursor.execute('''
                        INSERT INTO buracos 
                        (detection_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, confianca, distancia_m, largura_m)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (detection_id, int(x1), int(y1), int(x2), int(y2), float(conf), 
                          float(dist_m) if dist_m else None, float(width_m) if width_m else None))
                
                conn.commit()
                conn.close()
                print(f"✅ [DB] Detecção salva no banco: ID={detection_id}, Buracos={len(boxes)}")
            except Exception as e:
                print(f"❌ [DB] Erro ao salvar detecção: {e}")
                import traceback
                traceback.print_exc()
            conn.close()
            return detection_id
    
    def get_recent(self, limit=20):
        """Retorna detecções recentes com seus buracos"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Busca detecções
            cursor.execute(
                'SELECT * FROM detections ORDER BY id DESC LIMIT ?',
                (limit,)
            )
            detections = []
            
            for row in cursor.fetchall():
                detection = dict(row)
                
                # Busca buracos desta detecção
                cursor.execute(
                    'SELECT * FROM buracos WHERE detection_id = ?',
                    (detection['id'],)
                )
                buracos = [dict(b) for b in cursor.fetchall()]
                detection['buracos'] = buracos
                detections.append(detection)
            
            conn.close()
            return detections
    
    def get_by_id(self, detection_id):
        """Retorna detecção específica com seus buracos"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM detections WHERE id = ?', (detection_id,))
            row = cursor.fetchone()
            
            if not row:
                conn.close()
                return None
            
            detection = dict(row)
            cursor.execute('SELECT * FROM buracos WHERE detection_id = ?', (detection_id,))
            detection['buracos'] = [dict(b) for b in cursor.fetchall()]
            
            conn.close()
            return detection
    
    def get_stats(self):
        """Retorna estatísticas gerais"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM detections')
            total_detections = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM buracos')
            total_buracos = cursor.fetchone()[0]
            
            conn.close()
            return {
                'total_detections': total_detections,
                'total_buracos': total_buracos
            }

app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
db_manager = DatabaseManager()
frame_global = None  # Frame com overlay enviado para o stream
latest_frame = None  # Frame bruto mais recente da câmera
detection_boxes = []  # Lista de boxes atuais (x1,y1,x2,y2,conf)
detection_text = "Inicializando..."
detection_color = (0, 255, 0)
detection_counter = 0
lock = threading.Lock()

# LIDAR state
lidar_data = {}
lidar_lock = threading.Lock()
LIDAR_PORT = "/dev/ttyUSB0"  # porta padrão USB
LIDAR_BAUD = 115200
CAM_HFOV_DEG = 70.0  # FOV horizontal aproximado da câmera (ajuste se tiver valor exato)
LIDAR_SECTOR_DEG = 5  # agregação em setores de 5 graus

def generate_frames():
    """Gera frames para o stream MJPEG"""
    global frame_global
    while True:
        with lock:
            if frame_global is not None:
                ret, buffer = cv2.imencode('.jpg', frame_global)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + f'{len(frame_bytes)}'.encode() + b'\r\n\r\n' +
                           frame_bytes + b'\r\n')
        time.sleep(0.03)

@app.route('/video_feed')
def video_feed():
    """Rota para o stream de vídeo"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    """Página inicial com Vue.js"""
    return render_template('index.html')

@app.route('/lidar')
def lidar_fullscreen():
    """Página LIDAR em tela cheia"""
    return render_template('lidar.html')

@app.route('/api/lidar/latest')
def lidar_latest():
    """Retorna leitura agregada do LIDAR por setor."""
    with lidar_lock:
        data = dict(lidar_data)
    return jsonify({
        "sectors": data,
        "sector_deg": LIDAR_SECTOR_DEG,
        "port": LIDAR_PORT,
        "baud": LIDAR_BAUD,
        "available": HAS_RPLIDAR and bool(data)
    })

@app.route('/api/detections/recent')
def get_recent_detections():
    """Retorna as detecções mais recentes do banco"""
    detections = db_manager.get_recent(limit=20)
    return jsonify({"detections": detections, "total": len(detections)})

@app.route('/api/detections/stats')
def get_detection_stats():
    """Retorna estatísticas gerais"""
    stats = db_manager.get_stats()
    return jsonify(stats)

@app.route('/api/detections/<int:detection_id>')
def get_detection(detection_id):
    """Retorna detalhes de uma detecção específica"""
    det = db_manager.get_by_id(detection_id)
    if det:
        return jsonify(det)
    return jsonify({"error": "Detecção não encontrada"}), 404

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Limpa todo o histórico de detecções e imagens"""
    import os
    import shutil
    try:
        # Deleta o banco de dados
        db_file = '/home/suple/Desktop/suple360v2/deteccoes/detections.db'
        if os.path.exists(db_file):
            os.remove(db_file)
            print("[INFO] Banco de dados deletado")
        
        # Deleta todas as imagens
        deteccoes_dir = '/home/suple/Desktop/suple360v2/deteccoes'
        if os.path.exists(deteccoes_dir):
            for file in os.listdir(deteccoes_dir):
                if file.endswith('.jpg'):
                    file_path = os.path.join(deteccoes_dir, file)
                    os.remove(file_path)
                    print(f"[INFO] Imagem deletada: {file}")
        
        # Reinicializa o banco de dados
        db_manager._init_db()
        print("[INFO] Histórico completamente limpo e banco reinicializado")
        
        return jsonify({"success": True, "message": "Histórico limpo com sucesso"})
    except Exception as e:
        print(f"[ERRO] Ao limpar histórico: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/db-info', methods=['GET'])
def db_info():
    """Retorna informações sobre o banco de dados - contagem de registros"""
    try:
        stats = db_manager.get_stats()
        import os
        db_path = '/home/suple/Desktop/suple360v2/deteccoes/detections.db'
        db_exists = os.path.exists(db_path)
        db_size = os.path.getsize(db_path) if db_exists else 0
        
        return jsonify({
            "success": True,
            "db_exists": db_exists,
            "db_size_bytes": db_size,
            "total_detections": stats.get('total_detections', 0),
            "total_potholes": stats.get('total_potholes', 0)
        })
    except Exception as e:
        print(f"[ERRO] Ao obter info do DB: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/test-lidar', methods=['GET'])
def test_lidar():
    """Retorna dados atuais do LIDAR para teste de distâncias"""
    with lidar_lock:
        data = dict(lidar_data)
    
    if not data:
        return jsonify({"success": False, "error": "LIDAR offline ou sem dados"}), 503
    
    # Processa os dados para mostrar distâncias
    results = []
    for sector_id, measurements in data.items():
        if measurements:
            distances = [m[0] for m in measurements]
            if distances:
                avg_distance = sum(distances) / len(distances)
                min_distance = min(distances)
                max_distance = max(distances)
                results.append({
                    "sector": sector_id,
                    "angle_deg": sector_id * LIDAR_SECTOR_DEG,
                    "num_points": len(distances),
                    "avg_distance_m": round(avg_distance, 2),
                    "min_distance_m": round(min_distance, 2),
                    "max_distance_m": round(max_distance, 2)
                })
    
    return jsonify({"success": True, "lidar_test": results, "total_sectors": len(results)})

@app.route('/deteccoes/<path:filename>')
def serve_detection_image(filename):
    """Serve imagens de detecção"""
    import os.path
    # Caminho absoluto da pasta de detecções
    deteccoes_dir = '/home/suple/Desktop/suple360v2/deteccoes'
    filepath = os.path.join(deteccoes_dir, filename)
    
    if os.path.exists(filepath) and os.path.isfile(filepath):
        return send_file(filepath, mimetype='image/jpeg')
    
    # Log para debug
    print(f"[ERRO] Imagem não encontrada: {filepath}")
    return jsonify({"error": f"Imagem não encontrada: {filename}"}), 404

def draw_overlays(frame, boxes, text, color, frame_id=None):
    """Desenha boxes e textos no frame."""
    if frame_id is not None:
        cv2.putText(frame, f"Frame {frame_id}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    for item in boxes:
        if len(item) == 5:
            x1, y1, x2, y2, conf = item
            dist_m = None
            width_m = None
        else:
            x1, y1, x2, y2, conf, dist_m, width_m = item
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        if dist_m is not None and width_m is not None:
            label = f"Buraco {conf:.2f} | {dist_m:.1f}m | L~{width_m:.2f}m"
        elif dist_m is not None:
            label = f"Buraco {conf:.2f} | {dist_m:.1f}m"
        else:
            label = f"Buraco {conf:.2f}"
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
    if text:
        cv2.putText(frame, text, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame


def detection_loop(model, screenshot_dir):
    """Thread de detecção: usa frame reduzido e atualiza boxes."""
    global latest_frame, detection_boxes, detection_text, detection_color, detection_counter
    while True:
        with lock:
            if latest_frame is None:
                frame = None
            else:
                frame = latest_frame.copy()
        if frame is None:
            time.sleep(0.01)
            continue

        # Reduz a imagem para detecção (mais rápido) – e.g., 640x360
        target_w, target_h = 640, 360
        det_input = cv2.resize(frame, (target_w, target_h))
        results = model(det_input)

        # Escala boxes de volta para a resolução original
        scale_x = frame.shape[1] / target_w
        scale_y = frame.shape[0] / target_h
        new_boxes = []
        frame_w = frame.shape[1]

        # Lê snapshot do LIDAR para fusão
        with lidar_lock:
            lidar_snapshot = dict(lidar_data)

        def sector_to_distance(angle_deg):
            if not lidar_snapshot:
                return None
            # Normaliza ângulo para 0..360 e encontra setor mais próximo
            angle_norm = angle_deg % 360
            sector = int(round(angle_norm / LIDAR_SECTOR_DEG) * LIDAR_SECTOR_DEG)
            return lidar_snapshot.get(str(sector)) or lidar_snapshot.get(sector)

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(float, box.xyxy[0])
                x1 = int(x1 * scale_x)
                x2 = int(x2 * scale_x)
                y1 = int(y1 * scale_y)
                y2 = int(y2 * scale_y)
                conf = float(box.conf[0])

                # Estima ângulo do centro do box em relação ao centro da câmera
                x_center = (x1 + x2) / 2.0
                rel = (x_center / frame_w) - 0.5  # -0.5 a 0.5
                angle_deg = rel * CAM_HFOV_DEG
                dist_m = sector_to_distance(angle_deg)

                width_m = None
                if dist_m is not None:
                    # largura angular do box => largura aproximada no chão
                    box_ang = ((x2 - x1) / frame_w) * CAM_HFOV_DEG
                    width_m = max(0.0, dist_m * 2 * 3.14159 * (box_ang / 360.0))

                new_boxes.append((x1, y1, x2, y2, conf, dist_m, width_m))

        # Atualiza estado global
        if new_boxes:
            detection_counter += 1
            text = f"✓ BURACO DETECTADO! ({len(new_boxes)} objeto(s))"
            color = (0, 0, 255)

            # Salva frame anotado
            annotated = draw_overlays(frame.copy(), new_boxes, text, color)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            filename = f"buraco_{time.strftime('%Y%m%d_%H%M%S')}_{detection_counter}.jpg"
            full_path = f"{screenshot_dir}/{filename}"
            cv2.imwrite(full_path, annotated)
            print(f"✓ Buraco detectado! Foto {detection_counter} salva: {full_path}")
            
            # Registra no banco de dados SQLite (salva apenas o nome do arquivo)
            db_manager.add_detection(
                photo_path=filename,
                boxes=new_boxes,
                timestamp=timestamp
            )
        else:
            text = "Nenhum buraco detectado"
            color = (0, 255, 0)

        with lock:
            detection_boxes = new_boxes
            detection_text = text
            detection_color = color


def capture_loop(camera):
    """Thread de captura: mantém stream fluido e aplica overlay com últimas detecções."""
    global frame_global, latest_frame, detection_boxes, detection_text, detection_color
    frame_count = 0
    while True:
        frame = camera.capture_array()

        # Converte XBGR8888 -> BGR e BGR -> RGB
        if frame.shape[2] == 4:
            frame = frame[:, :, :3]
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        frame_count += 1

        # Pega estado de detecção atual e desenha overlay
        with lock:
            latest_frame = frame.copy()
            boxes = detection_boxes.copy()
            text = detection_text
            color = detection_color

        frame_vis = draw_overlays(frame.copy(), boxes, text, color, frame_id=frame_count)

        # Atualiza frame para o stream
        with lock:
            frame_global = frame_vis

def run_flask():
    """Inicia o servidor Flask em background"""
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    camera = None
    try:
        # Inicia servidor Flask
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Carrega YOLO
        model = YOLO('/home/suple/Desktop/suple360v2/model/best.pt')
        print("Modelo YOLO carregado com sucesso!")

        # Inicia câmera (1280x720 para balancear qualidade e velocidade)
        camera = picamera2.Picamera2()
        config = camera.create_preview_configuration(main={"size": (1280, 720)})
        camera.configure(config)
        camera.start()
        print("Câmera iniciada com sucesso!")
        print("Resolução: 1280x720")

        # Pasta de screenshots
        screenshot_dir = '/home/suple/Desktop/suple360v2/deteccoes'
        os.makedirs(screenshot_dir, exist_ok=True)

        print("Iniciando detecção de buracos...")
        print("Stream disponível em: http://localhost:5000")

        # Thread do LIDAR (opcional)
        if HAS_RPLIDAR:
            def lidar_thread():
                global lidar_data
                while True:
                    lidar = None
                    try:
                        lidar = RPLidar(LIDAR_PORT, baudrate=LIDAR_BAUD)
                        print(f"[LIDAR] Conectado e operacional em {LIDAR_PORT} @ {LIDAR_BAUD}")

                        for scan in lidar.iter_scans(max_buf_meas=500):
                            agg = {}
                            for meas in scan:
                                try:
                                    angle = meas[1] if len(meas) > 1 else None
                                    distance = meas[2] if len(meas) > 2 else None
                                    if angle is None or distance is None or distance <= 0:
                                        continue
                                    sector = int(round(angle / LIDAR_SECTOR_DEG) * LIDAR_SECTOR_DEG) % 360
                                    agg[sector] = min(agg.get(sector, distance), distance)
                                except Exception:
                                    continue

                            with lidar_lock:
                                lidar_data = dict(agg)
                    except Exception as e:
                        print(f"[LIDAR] Erro: {e}")
                        time.sleep(1)
                    finally:
                        if lidar:
                            try:
                                lidar.stop()
                                lidar.disconnect()
                            except Exception:
                                pass

            threading.Thread(target=lidar_thread, daemon=True).start()
            print(f"LIDAR: iniciando leitura em {LIDAR_PORT} @ {LIDAR_BAUD}")
        else:
            print("LIDAR não disponível (instale 'pip install rplidar' e confirme /dev/ttyUSB0)")

        # Threads: captura fluida + detecção assíncrona
        capture_thread = threading.Thread(target=capture_loop, args=(camera,), daemon=True)
        detect_thread = threading.Thread(target=detection_loop, args=(model, screenshot_dir), daemon=True)
        capture_thread.start()
        detect_thread.start()

        # Mantém a thread principal viva
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nEncerrando detecção...")
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        if camera:
            camera.stop()
            print("Câmera parada.")
