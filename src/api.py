from flask import Flask, Response, render_template, jsonify, send_file, request
import cv2
import time
import os
import shutil
import base64
import numpy as np


def create_app(db_manager, camera_manager, lidar_manager, mapper=None):
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
    
    @app.route('/map')
    def map_view():
        """Página do mapa 2D"""
        return render_template('map.html')
    
    @app.route('/api/map/current')
    def get_current_map():
        """Retorna imagem do mapa atual em base64"""
        if not mapper:
            return jsonify({"error": "Mapper não disponível"}), 503
        
        try:
            mapa_img = mapper.render()
            _, buffer = cv2.imencode('.png', mapa_img)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            stats = mapper.get_statistics()
            
            return jsonify({
                "success": True,
                "image": f"data:image/png;base64,{img_base64}",
                "statistics": stats
            })
        except Exception as e:
            print(f"[ERRO] Ao gerar mapa: {str(e)}")
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/map/statistics')
    def get_map_statistics():
        """Retorna estatísticas do mapa"""
        if not mapper:
            return jsonify({"error": "Mapper não disponível"}), 503
        
        try:
            stats = mapper.get_statistics()
            return jsonify(stats)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/map/clear', methods=['POST'])
    def clear_map():
        """Limpa o mapa"""
        if not mapper:
            return jsonify({"error": "Mapper não disponível"}), 503
        
        try:
            mapper.clear()
            return jsonify({"success": True, "message": "Mapa limpo"})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/map/export')
    def export_map():
        """Exporta mapa como imagem PNG"""
        if not mapper:
            return jsonify({"error": "Mapper não disponível"}), 503
        
        try:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"mapa_{timestamp}.png"
            filepath = f"/home/suple/Desktop/suple360v2/deteccoes/{filename}"
            
            mapper.export_image(filepath)
            
            return jsonify({
                "success": True,
                "filepath": filepath,
                "filename": filename
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==========================================
    # ROTAS DE CALIBRAÇÃO (Fase 6)
    # ==========================================
    
    @app.route('/calibracao')
    def calibracao_page():
        """Página de calibração"""
        return render_template('calibracao.html')
    
    @app.route('/api/gerar_padrao_xadrez')
    def gerar_padrao_xadrez():
        """Gera PDF com padrão xadrez"""
        try:
            from pattern_generator import CalibrationPatternGenerator
            
            generator = CalibrationPatternGenerator()
            output_path = '/home/suple/Desktop/suple360v2/deteccoes/padrao_xadrez.pdf'
            
            generator.gerar_padrao_xadrez(
                pattern_size=(9, 6),
                square_size_mm=25,
                output_path=output_path
            )
            
            return send_file(
                output_path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='padrao_xadrez.pdf'
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/gerar_aruco_markers')
    def gerar_aruco_markers():
        """DEPRECADO - Agora usa imagem existente"""
        return jsonify({"error": "Use /api/baixar_aruco_imagem"}), 410
    
    @app.route('/api/baixar_aruco_imagem')
    def baixar_aruco_imagem():
        """Baixa imagem ArUco existente (do OpenCV docs)"""
        try:
            imagem_path = '/home/suple/Desktop/suple360v2/singlemarkerssource.jpg'
            
            if not os.path.exists(imagem_path):
                return jsonify({"error": "Imagem ArUco não encontrada"}), 404
            
            return send_file(
                imagem_path,
                mimetype='image/jpeg',
                as_attachment=True,
                download_name='aruco_markers_opencv.jpg'
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    # ==========================================
    # ROTAS DE CALIBRAÇÃO EM TEMPO REAL
    # ==========================================
    
    calibration_images = []
    current_frame_status = {'pattern_detected': False, 'quality': 0}
    
    @app.route('/calibracao_live')
    def calibracao_live_page():
        """Página de calibração em tempo real"""
        return render_template('calibracao_live.html')
    
    def generate_calibration_frames():
        """Gera frames com overlay de calibração"""
        while True:
            frame = camera_manager.get_stream_frame()
            if frame is not None:
                pattern_type = getattr(generate_calibration_frames, 'pattern_type', 'chessboard')
                
                if pattern_type == 'chessboard':
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    ret, corners = cv2.findChessboardCorners(gray, (9, 6), None)
                    
                    if ret:
                        cv2.drawChessboardCorners(frame, (9, 6), corners, ret)
                        quality = min(100, int((len(corners) / 54) * 100))
                        current_frame_status['pattern_detected'] = True
                        current_frame_status['quality'] = quality
                        
                        cv2.putText(frame, f"Padrão detectado! Qualidade: {quality}%", 
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        current_frame_status['pattern_detected'] = False
                        current_frame_status['quality'] = 0
                        cv2.putText(frame, "Aguardando padrão xadrez...", 
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                elif pattern_type == 'aruco':
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
                    parameters = cv2.aruco.DetectorParameters()
                    detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
                    corners, ids, rejected = detector.detectMarkers(gray)
                    
                    if ids is not None and len(ids) > 0:
                        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                        quality = min(100, len(ids) * 20)
                        current_frame_status['pattern_detected'] = True
                        current_frame_status['quality'] = quality
                        
                        cv2.putText(frame, f"{len(ids)} markers detectados! Qualidade: {quality}%", 
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    else:
                        current_frame_status['pattern_detected'] = False
                        current_frame_status['quality'] = 0
                        cv2.putText(frame, "Aguardando markers ArUco...", 
                                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-Length: ' + f'{len(frame_bytes)}'.encode() + b'\r\n\r\n' +
                           frame_bytes + b'\r\n')
            time.sleep(0.03)
    
    @app.route('/api/calibracao_stream')
    def calibracao_stream():
        """Stream de vídeo com detecção de padrões"""
        return Response(generate_calibration_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @app.route('/api/calibracao_status')
    def calibracao_status():
        """Retorna status atual da detecção"""
        return jsonify(current_frame_status)
    
    @app.route('/api/calibracao_capturar', methods=['POST'])
    def calibracao_capturar():
        """Captura frame para calibração"""
        try:
            import json
            data = json.loads(request.data)
            pattern_type = data.get('pattern_type', 'chessboard')
            
            generate_calibration_frames.pattern_type = pattern_type
            
            frame = camera_manager.get_stream_frame()
            if frame is None:
                return jsonify({"success": False, "error": "Câmera não disponível"}), 503
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            if pattern_type == 'chessboard':
                ret, corners = cv2.findChessboardCorners(gray, (9, 6), None)
                if not ret:
                    return jsonify({"success": False, "error": "Padrão xadrez não detectado"}), 400
                
                quality = min(100, int((len(corners) / 54) * 100))
                calibration_images.append({
                    'frame': frame.copy(),
                    'gray': gray.copy(),
                    'corners': corners,
                    'pattern_type': 'chessboard',
                    'quality': quality
                })
                
            elif pattern_type == 'aruco':
                aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
                parameters = cv2.aruco.DetectorParameters()
                detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
                corners, ids, rejected = detector.detectMarkers(gray)
                
                if ids is None or len(ids) == 0:
                    return jsonify({"success": False, "error": "Markers ArUco não detectados"}), 400
                
                quality = min(100, len(ids) * 20)
                calibration_images.append({
                    'frame': frame.copy(),
                    'gray': gray.copy(),
                    'corners': corners,
                    'ids': ids,
                    'pattern_type': 'aruco',
                    'quality': quality
                })
            
            return jsonify({
                "success": True,
                "captured": len(calibration_images),
                "quality": quality
            })
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/calibracao_executar', methods=['POST'])
    def calibracao_executar():
        """Executa calibração com as imagens capturadas"""
        try:
            import json
            import numpy as np
            
            if len(calibration_images) < 10:
                return jsonify({
                    "success": False,
                    "error": f"Mínimo de 10 fotos necessárias. Capturadas: {len(calibration_images)}"
                }), 400
            
            data = json.loads(request.data)
            pattern_type = data.get('pattern_type', 'chessboard')
            
            objpoints = []
            imgpoints = []
            
            if pattern_type == 'chessboard':
                objp = np.zeros((6*9, 3), np.float32)
                objp[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2) * 0.025
                
                for img_data in calibration_images:
                    if img_data['pattern_type'] == 'chessboard':
                        objpoints.append(objp)
                        imgpoints.append(img_data['corners'])
                
                h, w = calibration_images[0]['gray'].shape
                ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                    objpoints, imgpoints, (w, h), None, None
                )
                
            elif pattern_type == 'aruco':
                # Para markers individuais, usamos método similar ao xadrez
                # mas com detecção de cada marker separadamente
                
                # Coleta todos os corners e IDs de todas as imagens
                all_corners = []
                all_ids = []
                all_counter = []
                
                for img_data in calibration_images:
                    if img_data['pattern_type'] == 'aruco':
                        all_corners.append(img_data['corners'])
                        all_ids.append(img_data['ids'])
                        # Contador para manter rastreamento de qual imagem
                        all_counter.append(len(img_data['ids']))
                
                # Tamanho do marker em metros (50mm = 0.05m)
                marker_length = 0.05
                
                # Cria board CharucoBoard ou usa calibrateCameraCharuco
                # Como temos markers individuais, vamos criar pontos 3D manualmente
                objpoints_aruco = []
                imgpoints_aruco = []
                
                for corners_set, ids_set in zip(all_corners, all_ids):
                    if ids_set is None or len(ids_set) == 0:
                        continue
                    
                    # Para cada marker detectado
                    for i, marker_id in enumerate(ids_set):
                        # Corners do marker (4 cantos)
                        marker_corners = corners_set[i][0]
                        
                        # Pontos 3D do marker (plano Z=0)
                        # Cantos do marker em ordem: top-left, top-right, bottom-right, bottom-left
                        obj_pts = np.array([
                            [-marker_length/2,  marker_length/2, 0],
                            [ marker_length/2,  marker_length/2, 0],
                            [ marker_length/2, -marker_length/2, 0],
                            [-marker_length/2, -marker_length/2, 0]
                        ], dtype=np.float32)
                        
                        objpoints_aruco.append(obj_pts)
                        imgpoints_aruco.append(marker_corners.astype(np.float32))
                
                if len(objpoints_aruco) < 4:
                    return jsonify({"success": False, "error": "Poucos markers detectados. Capture mais fotos."}), 400
                
                h, w = calibration_images[0]['gray'].shape
                ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                    objpoints_aruco, imgpoints_aruco, (w, h), None, None
                )
                
                objpoints = objpoints_aruco
                imgpoints = imgpoints_aruco
            
            if not ret:
                return jsonify({"success": False, "error": "Falha na calibração"}), 500
            
            import time
            timestamp = int(time.time())
            output_file = f'/home/suple/Desktop/suple360v2/calibracao_{pattern_type}.npz'
            np.savez(
                output_file,
                camera_matrix=mtx,
                dist_coeffs=dist,
                pattern_type=pattern_type,
                num_images=len(calibration_images),
                timestamp=timestamp
            )
            
            mean_error = 0
            for i in range(len(objpoints)):
                imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], mtx, dist)
                error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
                mean_error += error
            mean_error /= len(objpoints)
            
            return jsonify({
                "success": True,
                "reprojection_error": mean_error,
                "focal_x": float(mtx[0, 0]),
                "focal_y": float(mtx[1, 1]),
                "center_x": float(mtx[0, 2]),
                "center_y": float(mtx[1, 2]),
                "calibration_file": output_file,
                "num_images": len(calibration_images)
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/calibracao_resetar', methods=['POST'])
    def calibracao_resetar():
        """Reseta dados de calibração"""
        calibration_images.clear()
        current_frame_status['pattern_detected'] = False
        current_frame_status['quality'] = 0
        return jsonify({"success": True, "message": "Dados resetados"})
    
    @app.route('/api/calibracao_listar')
    def calibracao_listar():
        """Lista calibrações salvas"""
        try:
            import glob
            import numpy as np
            
            calibrations = []
            pattern = '/home/suple/Desktop/suple360v2/calibracao_*.npz'
            
            for filepath in glob.glob(pattern):
                try:
                    data = np.load(filepath, allow_pickle=True)
                    mtx = data['camera_matrix']
                    pattern_type = str(data['pattern_type'])
                    num_images = int(data['num_images'])
                    timestamp = int(data['timestamp']) if 'timestamp' in data else 0
                    
                    # Calcula erro de reprojeção (estimado)
                    # Em produção real, você salvaria isso durante calibração
                    reprojection_error = 0.5  # Placeholder
                    
                    calibrations.append({
                        'filename': os.path.basename(filepath),
                        'pattern_type': pattern_type,
                        'num_images': num_images,
                        'focal_x': float(mtx[0, 0]),
                        'focal_y': float(mtx[1, 1]),
                        'center_x': float(mtx[0, 2]),
                        'center_y': float(mtx[1, 2]),
                        'reprojection_error': reprojection_error,
                        'timestamp': timestamp
                    })
                except Exception as e:
                    print(f"Erro ao ler {filepath}: {e}")
                    continue
            
            # Ordena por timestamp (mais recente primeiro)
            calibrations.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return jsonify({"success": True, "calibrations": calibrations})
            
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/calibracao_deletar', methods=['POST'])
    def calibracao_deletar():
        """Deleta calibração salva"""
        try:
            import json
            data = json.loads(request.data)
            filename = data.get('filename', '')
            
            if not filename or '..' in filename:
                return jsonify({"success": False, "error": "Nome inválido"}), 400
            
            filepath = f'/home/suple/Desktop/suple360v2/{filename}'
            
            if os.path.exists(filepath) and filepath.endswith('.npz'):
                os.remove(filepath)
                return jsonify({"success": True, "message": "Calibração deletada"})
            else:
                return jsonify({"success": False, "error": "Arquivo não encontrado"}), 404
                
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    return app
