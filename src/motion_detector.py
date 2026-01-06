"""
Módulo de Detecção de Movimento
================================

Detecta quando há movimento significativo na cena para evitar
reprocessamento desnecessário de frames estáticos.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from typing import Tuple


class MotionDetector:
    """
    Detector de movimento para otimização de processamento.
    
    Estratégias:
    - Background subtraction (MOG2)
    - Frame differencing
    - Threshold de movimento configurável
    """
    
    def __init__(self, method='frame_diff', threshold=0.02):
        """
        Inicializa detector de movimento.
        
        Args:
            method: Método de detecção
                - 'frame_diff': Diferença entre frames (rápido)
                - 'mog2': Background subtraction (preciso)
            threshold: Threshold de movimento (0-1)
                0.01 = muito sensível
                0.05 = pouco sensível
        """
        self.method = method
        self.threshold = threshold
        
        # Frame anterior (para frame_diff)
        self.prev_frame = None
        
        # Background subtractor (para MOG2)
        if method == 'mog2':
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=16,
                detectShadows=False
            )
        else:
            self.bg_subtractor = None
        
        # Estatísticas
        self.total_frames = 0
        self.motion_frames = 0
        self.static_frames = 0
    
    def has_motion(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detecta se há movimento significativo no frame.
        
        Args:
            frame: Frame atual (BGR)
            
        Returns:
            Tuple (has_motion, motion_score):
            - has_motion: True se há movimento
            - motion_score: Score de movimento (0-1)
        """
        self.total_frames += 1
        
        if self.method == 'frame_diff':
            has_motion, score = self._detect_frame_diff(frame)
        elif self.method == 'mog2':
            has_motion, score = self._detect_mog2(frame)
        else:
            # Padrão: sempre processar
            return True, 1.0
        
        # Atualiza estatísticas
        if has_motion:
            self.motion_frames += 1
        else:
            self.static_frames += 1
        
        return has_motion, score
    
    def _detect_frame_diff(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detecta movimento comparando com frame anterior.
        
        Método rápido e eficiente.
        
        Args:
            frame: Frame atual
            
        Returns:
            (has_motion, motion_score)
        """
        # Converte para escala de cinza e reduz resolução (performance)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (160, 120))
        gray_blur = cv2.GaussianBlur(gray_small, (5, 5), 0)
        
        # Primeiro frame: sem movimento detectável
        if self.prev_frame is None:
            self.prev_frame = gray_blur
            return True, 1.0
        
        # Calcula diferença absoluta
        diff = cv2.absdiff(self.prev_frame, gray_blur)
        
        # Threshold
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        
        # Calcula porcentagem de pixels diferentes
        motion_pixels = np.sum(thresh > 0)
        total_pixels = thresh.size
        motion_score = motion_pixels / total_pixels
        
        # Atualiza frame anterior
        self.prev_frame = gray_blur
        
        # Decide se há movimento
        has_motion = motion_score >= self.threshold
        
        return has_motion, float(motion_score)
    
    def _detect_mog2(self, frame: np.ndarray) -> Tuple[bool, float]:
        """
        Detecta movimento usando background subtraction (MOG2).
        
        Método mais preciso mas mais lento.
        
        Args:
            frame: Frame atual
            
        Returns:
            (has_motion, motion_score)
        """
        # Aplica background subtraction
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Remove ruído
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        
        # Calcula porcentagem de foreground
        motion_pixels = np.sum(fg_mask > 0)
        total_pixels = fg_mask.size
        motion_score = motion_pixels / total_pixels
        
        # Decide se há movimento
        has_motion = motion_score >= self.threshold
        
        return has_motion, float(motion_score)
    
    def reset(self):
        """Reseta detector (útil ao trocar de cena)."""
        self.prev_frame = None
        
        if self.bg_subtractor is not None:
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
                history=500,
                varThreshold=16,
                detectShadows=False
            )
    
    def get_stats(self) -> dict:
        """
        Retorna estatísticas de uso.
        
        Returns:
            Dict com estatísticas
        """
        skip_rate = (self.static_frames / self.total_frames * 100) if self.total_frames > 0 else 0
        
        return {
            'total_frames': self.total_frames,
            'motion_frames': self.motion_frames,
            'static_frames': self.static_frames,
            'skip_rate': round(skip_rate, 1),
            'estimated_speedup': round(1.0 / (1.0 - skip_rate/100), 2) if skip_rate < 100 else float('inf')
        }
