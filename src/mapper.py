import cv2
import numpy as np
import threading
from collections import deque
from map_utils import CoordinateConverter


class MapBuilder:
    """
    Constrói mapa 2D bird's eye view (visão de cima) dos buracos detectados.
    
    Funcionalidades:
    - Plotar buracos com cores por severidade
    - Mostrar dados do LIDAR em 360°
    - Trajetória do veículo (se houver movimento)
    - Exportar mapa como imagem
    """
    
    def __init__(self, size_m=20, resolution_px=800, vehicle_radius_m=1.0):
        """
        Inicializa o construtor de mapas.
        
        Args:
            size_m: Tamanho do mapa em metros (20 = mapa de 20x20 metros)
            resolution_px: Resolução do canvas em pixels (800x800)
            vehicle_radius_m: Raio do veículo em metros
        """
        self.size_m = size_m
        self.resolution_px = resolution_px
        self.vehicle_radius_m = vehicle_radius_m
        
        # Conversor de coordenadas
        self.converter = CoordinateConverter(size_m, resolution_px)
        
        # Lista de buracos mapeados
        self.buracos = []
        
        # Dados do LIDAR (último scan)
        self.lidar_points = []
        
        # Trajetória do veículo (histórico de posições)
        self.trajectory = deque(maxlen=100)
        
        # Lock para thread-safety
        self.lock = threading.Lock()
        
        # Cores por severidade (BGR)
        self.colors = {
            'leve': (0, 255, 0),      # Verde
            'media': (0, 165, 255),    # Laranja
            'grave': (0, 0, 255),      # Vermelho
            'desconhecida': (128, 128, 128)  # Cinza
        }
    
    def add_buraco(self, distancia_m, angulo_deg, severidade='media', area_m2=0.1, track_id=None):
        """
        Adiciona um buraco ao mapa.
        
        Args:
            distancia_m: Distância do buraco em metros
            angulo_deg: Ângulo do buraco em graus (0° = frente)
            severidade: Classificação (leve/media/grave)
            area_m2: Área do buraco em m²
            track_id: ID de tracking (para evitar duplicatas)
        """
        with self.lock:
            # Verifica se já existe (mesmo track_id)
            if track_id is not None:
                for b in self.buracos:
                    if b.get('track_id') == track_id:
                        # Atualiza posição existente
                        b['distancia_m'] = distancia_m
                        b['angulo_deg'] = angulo_deg
                        b['severidade'] = severidade
                        b['area_m2'] = area_m2
                        return
            
            # Converte coordenadas polares → cartesianas
            x_m, y_m = self.converter.polar_to_cartesian(distancia_m, angulo_deg)
            
            # Adiciona novo buraco
            self.buracos.append({
                'track_id': track_id,
                'x_m': x_m,
                'y_m': y_m,
                'distancia_m': distancia_m,
                'angulo_deg': angulo_deg,
                'severidade': severidade,
                'area_m2': area_m2
            })
    
    def add_lidar_scan(self, lidar_data):
        """
        Adiciona dados do LIDAR ao mapa.
        
        Args:
            lidar_data: Dict com setores {angulo: distancia_mm, ...}
        """
        with self.lock:
            self.lidar_points = []
            
            if not lidar_data:
                return
            
            for sector, distance_mm in lidar_data.items():
                try:
                    angle_deg = float(sector)
                    distance_m = distance_mm / 1000.0  # mm → metros
                    
                    # Converte para cartesiano
                    x_m, y_m = self.converter.polar_to_cartesian(distance_m, angle_deg)
                    self.lidar_points.append((x_m, y_m))
                except (ValueError, TypeError):
                    continue
    
    def render(self):
        """
        Renderiza o mapa completo como imagem OpenCV.
        
        Returns:
            numpy.ndarray: Imagem do mapa (BGR)
        """
        with self.lock:
            # Cria canvas branco
            canvas = np.ones((self.resolution_px, self.resolution_px, 3), dtype=np.uint8) * 255
            
            # Desenha componentes em ordem (background → foreground)
            self._draw_grid(canvas)
            self._draw_lidar(canvas)
            self._draw_trajectory(canvas)
            self._draw_buracos(canvas)
            self._draw_vehicle(canvas)
            self._draw_legend(canvas)
            
            return canvas
    
    def _draw_grid(self, canvas):
        """Desenha grid de referência no mapa."""
        grid_spacing_m = 2  # Linhas a cada 2 metros
        color = (200, 200, 200)
        
        for x_m in range(-int(self.size_m/2), int(self.size_m/2) + 1, grid_spacing_m):
            px, py1 = self.converter.world_to_pixel(x_m, self.size_m/2)
            _, py2 = self.converter.world_to_pixel(x_m, -self.size_m/2)
            cv2.line(canvas, (px, py1), (px, py2), color, 1)
        
        for y_m in range(-int(self.size_m/2), int(self.size_m/2) + 1, grid_spacing_m):
            px1, py = self.converter.world_to_pixel(-self.size_m/2, y_m)
            px2, _ = self.converter.world_to_pixel(self.size_m/2, y_m)
            cv2.line(canvas, (px1, py), (px2, py), color, 1)
        
        # Eixos principais
        center = self.converter.center_px
        cv2.line(canvas, (center, 0), (center, self.resolution_px), (150, 150, 150), 2)
        cv2.line(canvas, (0, center), (self.resolution_px, center), (150, 150, 150), 2)
    
    def _draw_lidar(self, canvas):
        """Desenha pontos do LIDAR no mapa."""
        for x_m, y_m in self.lidar_points:
            px, py = self.converter.world_to_pixel(x_m, y_m)
            if self.converter.is_inside_canvas(px, py):
                cv2.circle(canvas, (px, py), 2, (100, 100, 100), -1)
    
    def _draw_trajectory(self, canvas):
        """Desenha trajetória do veículo."""
        if len(self.trajectory) < 2:
            return
        
        points = [self.converter.world_to_pixel(x, y) for x, y in self.trajectory]
        points_array = np.array(points, dtype=np.int32)
        cv2.polylines(canvas, [points_array], False, (255, 200, 0), 2)
    
    def _draw_buracos(self, canvas):
        """Desenha buracos no mapa com cores por severidade."""
        for buraco in self.buracos:
            px, py = self.converter.world_to_pixel(buraco['x_m'], buraco['y_m'])
            
            if not self.converter.is_inside_canvas(px, py):
                continue
            
            # Raio proporcional à área
            raio_px = int(5 + min(buraco['area_m2'] * 100, 25))
            color = self.colors.get(buraco['severidade'], self.colors['desconhecida'])
            
            # Desenha círculo preenchido com borda
            cv2.circle(canvas, (px, py), raio_px, color, -1)
            cv2.circle(canvas, (px, py), raio_px, (0, 0, 0), 2)
            
            # Texto com distância
            dist_text = f"{buraco['distancia_m']:.1f}m"
            cv2.putText(canvas, dist_text, (px - 15, py - raio_px - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    
    def _draw_vehicle(self, canvas):
        """Desenha o veículo no centro do mapa."""
        center = self.converter.center_px
        vehicle_radius_px = int(self.vehicle_radius_m * self.converter.scale)
        
        # Círculo do veículo
        cv2.circle(canvas, (center, center), vehicle_radius_px, (255, 0, 0), -1)
        
        # Seta indicando frente
        arrow_length = int(vehicle_radius_px * 1.5)
        cv2.arrowedLine(canvas, (center, center),
                       (center, center - arrow_length),
                       (255, 255, 255), 3, tipLength=0.3)
    
    def _draw_legend(self, canvas):
        """Desenha legenda do mapa."""
        x, y, w, h = 10, 10, 150, 120
        
        # Fundo da legenda
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 255, 255), -1)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (0, 0, 0), 2)
        
        # Título
        cv2.putText(canvas, "Legenda", (x + 10, y + 25),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # Itens
        items = [("Leve", self.colors['leve']),
                ("Medio", self.colors['media']),
                ("Grave", self.colors['grave'])]
        
        y_offset = 50
        for label, color in items:
            cv2.circle(canvas, (x + 20, y + y_offset), 8, color, -1)
            cv2.circle(canvas, (x + 20, y + y_offset), 8, (0, 0, 0), 1)
            cv2.putText(canvas, label, (x + 35, y + y_offset + 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
            y_offset += 25
    
    def get_statistics(self):
        """Retorna estatísticas do mapa."""
        with self.lock:
            por_severidade = {}
            area_total = 0
            
            for buraco in self.buracos:
                sev = buraco['severidade']
                por_severidade[sev] = por_severidade.get(sev, 0) + 1
                area_total += buraco.get('area_m2', 0)
            
            return {
                'total_buracos': len(self.buracos),
                'por_severidade': por_severidade,
                'area_total_m2': round(area_total, 4),
                'lidar_points': len(self.lidar_points)
            }
    
    def clear(self):
        """Limpa todos os dados do mapa."""
        with self.lock:
            self.buracos = []
            self.lidar_points = []
            self.trajectory.clear()
    
    def export_image(self, filepath):
        """Exporta mapa como imagem PNG."""
        mapa = self.render()
        cv2.imwrite(filepath, mapa)
        print(f"✅ Mapa exportado: {filepath}")
