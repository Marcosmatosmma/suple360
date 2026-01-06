import sqlite3
import threading
import os


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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                photo_path TEXT NOT NULL,
                num_buracos INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS buracos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                detection_id INTEGER NOT NULL,
                track_id INTEGER,
                bbox_x1 INTEGER,
                bbox_y1 INTEGER,
                bbox_x2 INTEGER,
                bbox_y2 INTEGER,
                confianca REAL,
                distancia_m REAL,
                largura_m REAL,
                altura_m REAL,
                area_m2 REAL,
                perimetro_m REAL,
                aspect_ratio REAL,
                circularidade REAL,
                convexidade REAL,
                orientacao_deg REAL,
                intensidade_media REAL,
                desvio_padrao REAL,
                contraste REAL,
                severidade TEXT,
                prioridade TEXT,
                FOREIGN KEY (detection_id) REFERENCES detections(id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_detection(self, photo_path, boxes, timestamp, analysis_data=None):
        """
        Adiciona detecção e seus buracos ao banco.
        
        Args:
            photo_path: Nome do arquivo da foto
            boxes: Lista de boxes detectados
            timestamp: Data/hora da detecção
            analysis_data: Lista de dicionários com análises OpenCV (opcional)
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute(
                    'INSERT INTO detections (timestamp, photo_path, num_buracos) VALUES (?, ?, ?)',
                    (timestamp, photo_path, len(boxes))
                )
                detection_id = cursor.lastrowid
                
                for idx, box in enumerate(boxes):
                    if len(box) == 7:
                        x1, y1, x2, y2, conf, dist_m, width_m = box
                    else:
                        x1, y1, x2, y2, conf = box[:5]
                        dist_m, width_m = None, None
                    
                    # Dados da análise OpenCV (se disponível)
                    analysis = analysis_data[idx] if analysis_data and idx < len(analysis_data) else {}
                    track_id = analysis.get('track_id')
                    
                    # Extrai dados de análise
                    dims = analysis.get('dimensoes_reais', {})
                    geom = analysis.get('geometria', {})
                    tex = analysis.get('textura', {})
                    classif = analysis.get('classificacao', {})
                    
                    cursor.execute('''
                        INSERT INTO buracos 
                        (detection_id, track_id, bbox_x1, bbox_y1, bbox_x2, bbox_y2, 
                         confianca, distancia_m, largura_m, altura_m, area_m2, perimetro_m,
                         aspect_ratio, circularidade, convexidade, orientacao_deg,
                         intensidade_media, desvio_padrao, contraste, severidade, prioridade)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        detection_id, 
                        track_id,
                        int(x1), int(y1), int(x2), int(y2),
                        float(conf),
                        float(dist_m) if dist_m else None,
                        dims.get('largura_m'),
                        dims.get('altura_m'),
                        dims.get('area_m2'),
                        dims.get('perimetro_m'),
                        geom.get('aspect_ratio'),
                        geom.get('circularidade'),
                        geom.get('convexidade'),
                        geom.get('orientacao_deg'),
                        tex.get('intensidade_media'),
                        tex.get('desvio_padrao'),
                        tex.get('contraste'),
                        classif.get('severidade'),
                        classif.get('prioridade')
                    ))
                
                conn.commit()
                conn.close()
                print(f"✅ [DB] Detecção salva no banco: ID={detection_id}, Buracos={len(boxes)}")
            except Exception as e:
                print(f"❌ [DB] Erro ao salvar detecção: {e}")
                import traceback
                traceback.print_exc()
            finally:
                conn.close()
            return detection_id
    
    def get_recent(self, limit=20):
        """Retorna detecções recentes com seus buracos"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                'SELECT * FROM detections ORDER BY id DESC LIMIT ?',
                (limit,)
            )
            detections = []
            
            for row in cursor.fetchall():
                detection = dict(row)
                
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
