import picamera2
import os
import time
import threading
from ultralytics import YOLO
from database import DatabaseManager
from lidar_manager import LidarManager
from camera import CameraManager
from detector import Detector
from api import create_app


def main():
    """Função principal de inicialização"""
    camera = None
    try:
        screenshot_dir = '/home/suple/Desktop/suple360v2/deteccoes'
        os.makedirs(screenshot_dir, exist_ok=True)
        
        db_manager = DatabaseManager()
        print("✓ Banco de dados inicializado")
        
        lidar_manager = LidarManager(
            port="/dev/ttyUSB0",
            baud=115200,
            sector_deg=5
        )
        lidar_manager.start()
        print("✓ LIDAR inicializado")
        
        model = YOLO('/home/suple/Desktop/suple360v2/model/best.pt')
        print("✓ Modelo YOLO carregado")
        
        camera = picamera2.Picamera2()
        config = camera.create_preview_configuration(main={"size": (1280, 720)})
        camera.configure(config)
        camera.start()
        print("✓ Câmera iniciada (1280x720)")
        
        camera_manager = CameraManager(camera)
        camera_manager.start()
        print("✓ Gerenciador de câmera iniciado")
        
        detector = Detector(
            model=model,
            db_manager=db_manager,
            lidar_manager=lidar_manager,
            camera_manager=camera_manager,
            screenshot_dir=screenshot_dir,
            cam_hfov_deg=70.0
        )
        detector.start()
        print("✓ Detector iniciado")
        
        app = create_app(db_manager, camera_manager, lidar_manager)
        
        def run_flask():
            app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        print("✓ Servidor Flask iniciado em http://0.0.0.0:5000")
        
        print("\n" + "="*50)
        print("Sistema iniciado com sucesso!")
        print("Acesse: http://localhost:5000")
        print("="*50 + "\n")
        
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nEncerrando sistema...")
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if camera:
            camera.stop()
            print("✓ Câmera parada")


if __name__ == "__main__":
    main()
