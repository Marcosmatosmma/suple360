import threading
import time

try:
    from rplidar import RPLidar
    HAS_RPLIDAR = True
except ImportError:
    HAS_RPLIDAR = False


class LidarManager:
    """Gerencia leitura e agregação de dados do LIDAR"""
    
    def __init__(self, port="/dev/ttyUSB0", baud=115200, sector_deg=5):
        self.port = port
        self.baud = baud
        self.sector_deg = sector_deg
        self.data = {}
        self.lock = threading.Lock()
        self.has_lidar = HAS_RPLIDAR
    
    def get_data(self):
        """Retorna snapshot dos dados atuais"""
        with self.lock:
            return dict(self.data)
    
    def sector_to_distance(self, angle_deg):
        """Retorna distância do setor mais próximo ao ângulo fornecido"""
        with self.lock:
            if not self.data:
                return None
            angle_norm = angle_deg % 360
            sector = int(round(angle_norm / self.sector_deg) * self.sector_deg)
            return self.data.get(str(sector)) or self.data.get(sector)
    
    def start(self):
        """Inicia thread de leitura do LIDAR"""
        if not self.has_lidar:
            print("LIDAR não disponível (instale 'pip install rplidar' e confirme /dev/ttyUSB0)")
            return
        
        def lidar_thread():
            while True:
                lidar = None
                try:
                    lidar = RPLidar(self.port, baudrate=self.baud)
                    print(f"[LIDAR] Conectado e operacional em {self.port} @ {self.baud}")
                    
                    for scan in lidar.iter_scans(max_buf_meas=500):
                        agg = {}
                        for meas in scan:
                            try:
                                angle = meas[1] if len(meas) > 1 else None
                                distance = meas[2] if len(meas) > 2 else None
                                if angle is None or distance is None or distance <= 0:
                                    continue
                                sector = int(round(angle / self.sector_deg) * self.sector_deg) % 360
                                agg[sector] = min(agg.get(sector, distance), distance)
                            except Exception:
                                continue
                        
                        with self.lock:
                            self.data = dict(agg)
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
        print(f"LIDAR: iniciando leitura em {self.port} @ {self.baud}")
