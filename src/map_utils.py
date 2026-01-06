import math
import numpy as np


class CoordinateConverter:
    """
    Conversões de coordenadas para mapeamento 2D.
    
    Responsabilidades:
    - Conversão polar → cartesiano
    - Conversão mundo (metros) → pixels
    - Normalização de ângulos
    """
    
    def __init__(self, size_m, resolution_px):
        """
        Inicializa conversor de coordenadas.
        
        Args:
            size_m: Tamanho do mapa em metros
            resolution_px: Resolução em pixels
        """
        self.size_m = size_m
        self.resolution_px = resolution_px
        self.scale = resolution_px / size_m  # pixels por metro
        self.center_px = resolution_px // 2
    
    def polar_to_cartesian(self, distancia_m, angulo_deg):
        """
        Converte coordenadas polares para cartesianas.
        
        Sistema de coordenadas:
        - Ângulo 0° = frente (norte)
        - Ângulo aumenta no sentido horário
        - X = direita, Y = frente
        
        Args:
            distancia_m: Distância em metros
            angulo_deg: Ângulo em graus
            
        Returns:
            tuple: (x_m, y_m) em metros
        """
        angulo_rad = math.radians(angulo_deg)
        x_m = distancia_m * math.sin(angulo_rad)
        y_m = distancia_m * math.cos(angulo_rad)
        return x_m, y_m
    
    def world_to_pixel(self, x_m, y_m):
        """
        Converte coordenadas do mundo (metros) para pixels do canvas.
        
        Args:
            x_m: Coordenada X em metros
            y_m: Coordenada Y em metros
            
        Returns:
            tuple: (px, py) em pixels
        """
        px = int(self.center_px + (x_m * self.scale))
        py = int(self.center_px - (y_m * self.scale))  # Inverte Y
        return px, py
    
    def is_inside_canvas(self, px, py):
        """
        Verifica se ponto em pixels está dentro do canvas.
        
        Args:
            px: Coordenada X em pixels
            py: Coordenada Y em pixels
            
        Returns:
            bool: True se está dentro do canvas
        """
        return 0 <= px < self.resolution_px and 0 <= py < self.resolution_px
