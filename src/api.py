from flask import Flask, Response, render_template, jsonify, send_file
import cv2
import time
import os
import shutil


def create_app(db_manager, camera_manager, lidar_manager):
    """Cria e configura aplicação Flask"""
    
    app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')
    
    def generate_frames():
        """Gera frames para o stream MJPEG"""
        while True:
            frame = camera_manager.get_stream_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
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
        """Retorna leitura agregada do LIDAR por setor"""
        data = lidar_manager.get_data()
        return jsonify({
            "sectors": data,
            "sector_deg": lidar_manager.sector_deg,
            "port": lidar_manager.port,
            "baud": lidar_manager.baud,
            "available": lidar_manager.has_lidar and bool(data)
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
        try:
            db_file = '/home/suple/Desktop/suple360v2/deteccoes/detections.db'
            if os.path.exists(db_file):
                os.remove(db_file)
                print("[INFO] Banco de dados deletado")
            
            deteccoes_dir = '/home/suple/Desktop/suple360v2/deteccoes'
            if os.path.exists(deteccoes_dir):
                for file in os.listdir(deteccoes_dir):
                    if file.endswith('.jpg'):
                        file_path = os.path.join(deteccoes_dir, file)
                        os.remove(file_path)
                        print(f"[INFO] Imagem deletada: {file}")
            
            db_manager._init_db()
            print("[INFO] Histórico completamente limpo e banco reinicializado")
            
            return jsonify({"success": True, "message": "Histórico limpo com sucesso"})
        except Exception as e:
            print(f"[ERRO] Ao limpar histórico: {str(e)}")
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/db-info', methods=['GET'])
    def db_info():
        """Retorna informações sobre o banco de dados"""
        try:
            stats = db_manager.get_stats()
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
        data = lidar_manager.get_data()
        
        if not data:
            return jsonify({"success": False, "error": "LIDAR offline ou sem dados"}), 503
        
        results = []
        for sector_id, measurements in data.items():
            if measurements:
                distances = [m[0] for m in measurements] if isinstance(measurements, list) else [measurements]
                if distances:
                    avg_distance = sum(distances) / len(distances)
                    min_distance = min(distances)
                    max_distance = max(distances)
                    results.append({
                        "sector": sector_id,
                        "angle_deg": int(sector_id) * lidar_manager.sector_deg if str(sector_id).isdigit() else 0,
                        "num_points": len(distances),
                        "avg_distance_m": round(avg_distance, 2),
                        "min_distance_m": round(min_distance, 2),
                        "max_distance_m": round(max_distance, 2)
                    })
        
        return jsonify({"success": True, "lidar_test": results, "total_sectors": len(results)})
    
    @app.route('/deteccoes/<path:filename>')
    def serve_detection_image(filename):
        """Serve imagens de detecção"""
        deteccoes_dir = '/home/suple/Desktop/suple360v2/deteccoes'
        filepath = os.path.join(deteccoes_dir, filename)
        
        if os.path.exists(filepath) and os.path.isfile(filepath):
            return send_file(filepath, mimetype='image/jpeg')
        
        print(f"[ERRO] Imagem não encontrada: {filepath}")
        return jsonify({"error": f"Imagem não encontrada: {filename}"}), 404
    
    return app
