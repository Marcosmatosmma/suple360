"""
Módulo de Estimativa de Profundidade Monocular
==============================================

Estima a profundidade de buracos usando análise de gradientes (Shape from Shading).
Combina informações visuais da câmera com dados do LIDAR para classificar profundidade.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from typing import Dict, Tuple, Optional


class DepthEstimator:
    """
    Estimador de profundidade monocular para buracos na via.
    
    Usa análise de gradientes e sombras para estimar profundidade relativa,
    classificando buracos como raso, médio ou profundo.
    """
    
    def __init__(self):
        """Inicializa o estimador de profundidade."""
        # Thresholds para classificação (baseados em análise de gradiente)
        self.PROFUNDIDADE_RASO = 15.0      # Gradiente médio < 15
        self.PROFUNDIDADE_MEDIO = 35.0     # Gradiente médio entre 15-35
        # > 35 = profundo
        
        # Pesos para combinação de features
        self.PESO_GRADIENTE = 0.4
        self.PESO_SOMBRA = 0.3
        self.PESO_INTENSIDADE = 0.3
    
    def estimar_profundidade(
        self, 
        roi: np.ndarray,
        distancia_lidar: float,
        contorno: np.ndarray
    ) -> Dict[str, any]:
        """
        Estima a profundidade de um buraco usando análise visual.
        
        Args:
            roi: Região de interesse (ROI) contendo o buraco
            distancia_lidar: Distância do LIDAR em metros
            contorno: Contorno do buraco (array de pontos)
            
        Returns:
            Dict com métricas de profundidade:
            - gradiente_medio: Intensidade média do gradiente
            - intensidade_sombra: % de pixels escuros (sombra)
            - variacao_intensidade: Variação de brilho interno
            - profundidade_score: Score combinado (0-100)
            - profundidade_cm: Estimativa em centímetros
            - classificacao: 'raso', 'medio' ou 'profundo'
        """
        if roi is None or roi.size == 0:
            return self._resultado_vazio()
        
        # Converte para escala de cinza se necessário
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()
        
        # 1. Análise de gradientes (detecta variação de profundidade)
        gradiente_medio = self._analisar_gradientes(gray, contorno)
        
        # 2. Análise de sombras (buracos profundos têm mais sombra)
        intensidade_sombra = self._analisar_sombras(gray, contorno)
        
        # 3. Variação de intensidade (diferença entre borda e centro)
        variacao_intensidade = self._analisar_intensidade(gray, contorno)
        
        # 4. Combina features para score final
        profundidade_score = self._calcular_score(
            gradiente_medio,
            intensidade_sombra,
            variacao_intensidade
        )
        
        # 5. Estima profundidade em cm usando distância LIDAR
        profundidade_cm = self._estimar_centimetros(
            profundidade_score,
            distancia_lidar
        )
        
        # 6. Classifica profundidade
        classificacao = self._classificar(gradiente_medio)
        
        return {
            'gradiente_medio': round(gradiente_medio, 2),
            'intensidade_sombra': round(intensidade_sombra, 2),
            'variacao_intensidade': round(variacao_intensidade, 2),
            'profundidade_score': round(profundidade_score, 2),
            'profundidade_cm': round(profundidade_cm, 2),
            'classificacao': classificacao
        }
    
    def _analisar_gradientes(self, gray: np.ndarray, contorno: np.ndarray) -> float:
        """
        Calcula gradiente médio dentro do contorno.
        Buracos profundos têm gradientes maiores (bordas mais acentuadas).
        
        Args:
            gray: Imagem em escala de cinza
            contorno: Contorno do buraco
            
        Returns:
            Gradiente médio (0-255)
        """
        # Calcula gradientes usando Sobel
        grad_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        
        # Magnitude do gradiente
        magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Cria máscara do contorno
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contorno], -1, 255, -1)
        
        # Calcula média apenas dentro do contorno
        pixels_roi = magnitude[mask == 255]
        
        if len(pixels_roi) == 0:
            return 0.0
        
        return float(np.mean(pixels_roi))
    
    def _analisar_sombras(self, gray: np.ndarray, contorno: np.ndarray) -> float:
        """
        Calcula porcentagem de pixels escuros (sombra) dentro do buraco.
        Buracos profundos tendem a ter mais sombra interna.
        
        Args:
            gray: Imagem em escala de cinza
            contorno: Contorno do buraco
            
        Returns:
            Porcentagem de sombra (0-100)
        """
        # Cria máscara do contorno
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contorno], -1, 255, -1)
        
        # Extrai pixels dentro do contorno
        pixels_roi = gray[mask == 255]
        
        if len(pixels_roi) == 0:
            return 0.0
        
        # Threshold para considerar pixel como "sombra" (escuro)
        # Usa Otsu para adaptação automática
        _, threshold = cv2.threshold(
            pixels_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        
        # Conta pixels abaixo do threshold
        pixels_escuros = np.sum(pixels_roi < threshold)
        porcentagem = (pixels_escuros / len(pixels_roi)) * 100
        
        return float(porcentagem)
    
    def _analisar_intensidade(self, gray: np.ndarray, contorno: np.ndarray) -> float:
        """
        Calcula diferença de intensidade entre borda e centro do buraco.
        Buracos profundos têm maior variação (centro mais escuro).
        
        Args:
            gray: Imagem em escala de cinza
            contorno: Contorno do buraco
            
        Returns:
            Diferença de intensidade (0-255)
        """
        # Cria máscara cheia
        mask_full = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask_full, [contorno], -1, 255, -1)
        
        # Cria máscara só da borda (5 pixels de espessura)
        mask_borda = np.zeros(gray.shape, dtype=np.uint8)
        cv2.drawContours(mask_borda, [contorno], -1, 255, 5)
        
        # Máscara do centro (área cheia - borda)
        mask_centro = cv2.subtract(mask_full, mask_borda)
        
        # Calcula intensidade média da borda e centro
        pixels_borda = gray[mask_borda == 255]
        pixels_centro = gray[mask_centro == 255]
        
        if len(pixels_borda) == 0 or len(pixels_centro) == 0:
            return 0.0
        
        intensidade_borda = np.mean(pixels_borda)
        intensidade_centro = np.mean(pixels_centro)
        
        # Diferença (borda - centro), buracos profundos têm valor positivo alto
        diferenca = abs(intensidade_borda - intensidade_centro)
        
        return float(diferenca)
    
    def _calcular_score(
        self, 
        gradiente: float, 
        sombra: float, 
        intensidade: float
    ) -> float:
        """
        Combina features visuais em score único de profundidade.
        
        Args:
            gradiente: Gradiente médio (0-255)
            sombra: Porcentagem de sombra (0-100)
            intensidade: Variação de intensidade (0-255)
            
        Returns:
            Score de profundidade (0-100)
        """
        # Normaliza gradiente e intensidade para 0-100
        gradiente_norm = (gradiente / 255.0) * 100
        intensidade_norm = (intensidade / 255.0) * 100
        
        # Combina com pesos
        score = (
            self.PESO_GRADIENTE * gradiente_norm +
            self.PESO_SOMBRA * sombra +
            self.PESO_INTENSIDADE * intensidade_norm
        )
        
        # Garante range 0-100
        return max(0.0, min(100.0, score))
    
    def _estimar_centimetros(self, score: float, distancia: float) -> float:
        """
        Converte score de profundidade em estimativa em centímetros.
        
        Usa correlação empírica: profundidade varia de 0.5cm a 15cm
        baseado em distância do LIDAR e score visual.
        
        Args:
            score: Score de profundidade (0-100)
            distancia: Distância do LIDAR em metros
            
        Returns:
            Profundidade estimada em centímetros
        """
        # Profundidade base do score (0.5cm a 10cm)
        profundidade_base = 0.5 + (score / 100.0) * 9.5
        
        # Fator de correção por distância (mais longe = menos preciso)
        # Assume precisão máxima até 2m, degrada linearmente até 5m
        if distancia <= 2.0:
            fator_distancia = 1.0
        elif distancia <= 5.0:
            fator_distancia = 1.0 - ((distancia - 2.0) / 3.0) * 0.3
        else:
            fator_distancia = 0.7
        
        # Profundidade final
        profundidade_cm = profundidade_base * fator_distancia
        
        return max(0.5, min(15.0, profundidade_cm))
    
    def _classificar(self, gradiente: float) -> str:
        """
        Classifica profundidade baseado no gradiente médio.
        
        Args:
            gradiente: Gradiente médio (0-255)
            
        Returns:
            'raso', 'medio' ou 'profundo'
        """
        if gradiente < self.PROFUNDIDADE_RASO:
            return 'raso'
        elif gradiente < self.PROFUNDIDADE_MEDIO:
            return 'medio'
        else:
            return 'profundo'
    
    def _resultado_vazio(self) -> Dict[str, any]:
        """Retorna resultado vazio para casos de erro."""
        return {
            'gradiente_medio': 0.0,
            'intensidade_sombra': 0.0,
            'variacao_intensidade': 0.0,
            'profundidade_score': 0.0,
            'profundidade_cm': 0.0,
            'classificacao': 'raso'
        }
