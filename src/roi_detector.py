"""
Módulo de Detecção de ROI (Region of Interest)
===============================================

Otimiza processamento focando apenas nas áreas relevantes da imagem.
Buracos não aparecem no céu, então processamos apenas a região inferior.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from typing import Tuple, List


class ROIDetector:
    """
    Detector de Região de Interesse para otimizar processamento.
    
    Estratégias:
    - Processar apenas metade/terço inferior da imagem
    - Detectar área de asfalto vs céu
    - Ajustar ROI dinamicamente baseado em conteúdo
    """
    
    def __init__(self, roi_mode='bottom_half'):
        """
        Inicializa detector de ROI.
        
        Args:
            roi_mode: Modo de ROI
                - 'bottom_half': Metade inferior (rápido)
                - 'bottom_two_thirds': 2/3 inferiores (balanceado)
                - 'adaptive': ROI adaptativo baseado em conteúdo
                - 'full': Imagem completa (sem otimização)
        """
        self.roi_mode = roi_mode
        
        # Cache para ROI adaptativo
        self.cached_roi = None
        self.cache_counter = 0
        self.cache_refresh_interval = 30  # Recalcula a cada 30 frames
    
    def get_roi(self, frame: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """
        Extrai região de interesse do frame.
        
        Args:
            frame: Frame completo
            
        Returns:
            Tuple (roi_frame, bbox):
            - roi_frame: Frame recortado da ROI
            - bbox: (x1, y1, x2, y2) coordenadas da ROI no frame original
        """
        h, w = frame.shape[:2]
        
        if self.roi_mode == 'full':
            # Sem otimização
            return frame, (0, 0, w, h)
        
        elif self.roi_mode == 'bottom_half':
            # Metade inferior (50% da imagem)
            y_start = h // 2
            roi = frame[y_start:h, 0:w]
            return roi, (0, y_start, w, h)
        
        elif self.roi_mode == 'bottom_two_thirds':
            # 2/3 inferiores (66% da imagem)
            y_start = h // 3
            roi = frame[y_start:h, 0:w]
            return roi, (0, y_start, w, h)
        
        elif self.roi_mode == 'adaptive':
            # ROI adaptativo baseado em segmentação
            return self._get_adaptive_roi(frame)
        
        else:
            # Padrão: metade inferior
            y_start = h // 2
            roi = frame[y_start:h, 0:w]
            return roi, (0, y_start, w, h)
    
    def _get_adaptive_roi(self, frame: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """
        Calcula ROI adaptativo detectando área de asfalto.
        
        Usa cache para não recalcular todo frame.
        
        Args:
            frame: Frame completo
            
        Returns:
            Tuple (roi_frame, bbox)
        """
        h, w = frame.shape[:2]
        
        # Usa cache se disponível
        if self.cached_roi is not None and self.cache_counter < self.cache_refresh_interval:
            self.cache_counter += 1
            x1, y1, x2, y2 = self.cached_roi
            return frame[y1:y2, x1:x2], self.cached_roi
        
        # Recalcula ROI
        self.cache_counter = 0
        
        # Converte para HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Segmenta asfalto (cinza escuro)
        # Hue: qualquer, Saturation: baixa, Value: médio-baixo
        lower_asphalt = np.array([0, 0, 20])
        upper_asphalt = np.array([180, 80, 120])
        
        mask = cv2.inRange(hsv, lower_asphalt, upper_asphalt)
        
        # Encontra maior região contínua
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            # Fallback: metade inferior
            y_start = h // 2
            bbox = (0, y_start, w, h)
        else:
            # Pega maior contorno
            largest = max(contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
            
            # Expande um pouco (margem de segurança)
            margin = 20
            x1 = max(0, x - margin)
            y1 = max(0, y - margin)
            x2 = min(w, x + cw + margin)
            y2 = min(h, y + ch + margin)
            
            bbox = (x1, y1, x2, y2)
        
        # Salva no cache
        self.cached_roi = bbox
        
        x1, y1, x2, y2 = bbox
        return frame[y1:y2, x1:x2], bbox
    
    def adjust_bbox_to_original(
        self, 
        bbox_in_roi: Tuple[int, int, int, int], 
        roi_bbox: Tuple[int, int, int, int]
    ) -> Tuple[int, int, int, int]:
        """
        Converte coordenadas do bbox na ROI para coordenadas no frame original.
        
        Args:
            bbox_in_roi: (x1, y1, x2, y2) na ROI
            roi_bbox: (x1, y1, x2, y2) da ROI no frame original
            
        Returns:
            (x1, y1, x2, y2) no frame original
        """
        roi_x1, roi_y1, _, _ = roi_bbox
        bbox_x1, bbox_y1, bbox_x2, bbox_y2 = bbox_in_roi
        
        # Adiciona offset da ROI
        return (
            bbox_x1 + roi_x1,
            bbox_y1 + roi_y1,
            bbox_x2 + roi_x1,
            bbox_y2 + roi_y1
        )
    
    def estimate_speedup(self) -> float:
        """
        Estima ganho de velocidade baseado no modo de ROI.
        
        Returns:
            Fator de speedup (ex: 2.0 = 2x mais rápido)
        """
        speedup_factors = {
            'full': 1.0,
            'bottom_half': 2.0,           # 50% menos pixels
            'bottom_two_thirds': 1.5,     # 33% menos pixels
            'adaptive': 1.8               # ~45% menos pixels (média)
        }
        
        return speedup_factors.get(self.roi_mode, 1.0)
