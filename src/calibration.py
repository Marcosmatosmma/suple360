import cv2
import numpy as np
import pickle
import os


class CameraCalibrator:
    """
    Calibração de câmera para correção de distorção e medições precisas.
    
    Funcionalidades:
    - Calibração com padrão xadrez
    - Matriz intrínseca da câmera
    - Coeficientes de distorção
    - Correção de imagens distorcidas
    - Salvar/carregar calibração
    """
    
    def __init__(self, calibration_file='calibration.pkl'):
        """
        Inicializa o calibrador.
        
        Args:
            calibration_file: Arquivo para salvar/carregar calibração
        """
        self.calibration_file = calibration_file
        self.camera_matrix = None  # Matriz intrínseca
        self.dist_coeffs = None    # Coeficientes de distorção
        self.is_calibrated = False
        
        # Tenta carregar calibração existente
        self.load_calibration()
    
    def calibrate_from_images(self, image_folder, pattern_size=(9, 6), square_size=0.025):
        """
        Calibra câmera usando imagens de tabuleiro xadrez.
        
        Args:
            image_folder: Pasta com imagens do padrão xadrez
            pattern_size: Número de cantos internos (largura, altura)
            square_size: Tamanho do quadrado em metros (ex: 2.5cm = 0.025m)
        
        Returns:
            bool: True se calibração foi bem-sucedida
        """
        # Critérios de terminação para detecção de cantos
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        
        # Prepara pontos do objeto (coordenadas 3D reais)
        objp = np.zeros((pattern_size[0] * pattern_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:pattern_size[0], 0:pattern_size[1]].T.reshape(-1, 2)
        objp *= square_size
        
        # Arrays para armazenar pontos
        objpoints = []  # Pontos 3D no mundo real
        imgpoints = []  # Pontos 2D na imagem
        
        # Busca imagens
        import glob
        images = glob.glob(os.path.join(image_folder, '*.jpg'))
        images += glob.glob(os.path.join(image_folder, '*.png'))
        
        if not images:
            print(f"❌ Nenhuma imagem encontrada em {image_folder}")
            return False
        
        print(f"📸 Processando {len(images)} imagens...")
        found_count = 0
        
        for img_path in images:
            img = cv2.imread(img_path)
            if img is None:
                continue
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Encontra cantos do tabuleiro
            ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)
            
            if ret:
                objpoints.append(objp)
                
                # Refina posição dos cantos
                corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
                imgpoints.append(corners_refined)
                found_count += 1
                print(f"  ✓ {os.path.basename(img_path)}: Cantos encontrados")
            else:
                print(f"  ✗ {os.path.basename(img_path)}: Padrão não detectado")
        
        if found_count < 10:
            print(f"❌ Poucas imagens válidas ({found_count}). Mínimo: 10")
            return False
        
        print(f"\n🔧 Calibrando com {found_count} imagens...")
        
        # Calibra câmera
        img_size = gray.shape[::-1]
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, img_size, None, None
        )
        
        if ret:
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            self.is_calibrated = True
            
            # Calcula erro de reprojeção
            mean_error = self._calculate_reprojection_error(objpoints, imgpoints, rvecs, tvecs)
            
            print(f"\n✅ Calibração concluída!")
            print(f"   Erro médio de reprojeção: {mean_error:.4f} pixels")
            print(f"\n📊 Matriz da câmera:")
            print(f"   fx={mtx[0,0]:.2f}, fy={mtx[1,1]:.2f}")
            print(f"   cx={mtx[0,2]:.2f}, cy={mtx[1,2]:.2f}")
            print(f"\n📐 Coeficientes de distorção:")
            print(f"   k1={dist[0,0]:.6f}, k2={dist[0,1]:.6f}")
            print(f"   p1={dist[0,2]:.6f}, p2={dist[0,3]:.6f}")
            
            self.save_calibration()
            return True
        
        return False
    
    def undistort_image(self, image):
        """
        Corrige distorção de uma imagem.
        
        Args:
            image: Imagem distorcida (numpy array BGR)
            
        Returns:
            numpy.ndarray: Imagem sem distorção
        """
        if not self.is_calibrated:
            return image
        
        return cv2.undistort(image, self.camera_matrix, self.dist_coeffs)
    
    def pixel_to_world_angle(self, px, py, image_width, image_height):
        """
        Converte coordenada de pixel para ângulo no mundo.
        
        Args:
            px, py: Coordenadas do pixel
            image_width, image_height: Dimensões da imagem
            
        Returns:
            tuple: (ângulo_x, ângulo_y) em graus
        """
        if not self.is_calibrated:
            # Aproximação sem calibração
            fov_x = 70.0  # FOV horizontal padrão
            angle_x = ((px / image_width) - 0.5) * fov_x
            angle_y = ((py / image_height) - 0.5) * fov_x * (image_height / image_width)
            return angle_x, angle_y
        
        # Com calibração precisa
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]
        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        
        angle_x = np.arctan((px - cx) / fx) * 180 / np.pi
        angle_y = np.arctan((py - cy) / fy) * 180 / np.pi
        
        return angle_x, angle_y
    
    def save_calibration(self):
        """Salva calibração em arquivo."""
        if not self.is_calibrated:
            return
        
        data = {
            'camera_matrix': self.camera_matrix,
            'dist_coeffs': self.dist_coeffs
        }
        
        with open(self.calibration_file, 'wb') as f:
            pickle.dump(data, f)
        
        print(f"💾 Calibração salva em {self.calibration_file}")
    
    def load_calibration(self):
        """Carrega calibração de arquivo."""
        if not os.path.exists(self.calibration_file):
            return False
        
        try:
            with open(self.calibration_file, 'rb') as f:
                data = pickle.load(f)
            
            self.camera_matrix = data['camera_matrix']
            self.dist_coeffs = data['dist_coeffs']
            self.is_calibrated = True
            
            print(f"✅ Calibração carregada de {self.calibration_file}")
            return True
        except Exception as e:
            print(f"⚠️ Erro ao carregar calibração: {e}")
            return False
    
    def _calculate_reprojection_error(self, objpoints, imgpoints, rvecs, tvecs):
        """
        Calcula erro médio de reprojeção.
        
        Args:
            objpoints: Pontos 3D do objeto
            imgpoints: Pontos 2D na imagem
            rvecs: Vetores de rotação
            tvecs: Vetores de translação
            
        Returns:
            float: Erro médio em pixels
        """
        total_error = 0
        total_points = 0
        
        for i in range(len(objpoints)):
            # Projeta pontos 3D de volta para 2D
            imgpoints2, _ = cv2.projectPoints(
                objpoints[i], rvecs[i], tvecs[i],
                self.camera_matrix, self.dist_coeffs
            )
            
            # Calcula erro
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            total_error += error
            total_points += 1
        
        return total_error / total_points if total_points > 0 else 0
