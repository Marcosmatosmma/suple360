"""
Módulo de Análise Avançada de Textura
======================================

Analisa características de textura detalhadas para classificar tipo de dano
e extrair métricas estatísticas avançadas.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from typing import Dict, Tuple


class TextureAnalyzer:
    """
    Analisador avançado de textura para buracos e danos na via.
    
    Extrai métricas estatísticas avançadas:
    - Entropia (desordem da textura)
    - GLCM (Gray-Level Co-occurrence Matrix)
    - Histogramas multi-canal (RGB, HSV)
    - Energia e homogeneidade
    """
    
    def __init__(self):
        """Inicializa o analisador de textura."""
        # Distâncias e ângulos para GLCM
        self.glcm_distances = [1]
        self.glcm_angles = [0, np.pi/4, np.pi/2, 3*np.pi/4]
        
        # Bins para histogramas
        self.hist_bins = 32
    
    def analisar_textura_avancada(
        self, 
        roi: np.ndarray,
        contorno: np.ndarray = None
    ) -> Dict[str, any]:
        """
        Análise completa de textura da região do buraco.
        
        Args:
            roi: Região de interesse (ROI) contendo o buraco
            contorno: Contorno do buraco (opcional, para máscara)
            
        Returns:
            Dict com métricas avançadas de textura:
            - entropia: Medida de desordem/aleatoriedade
            - energia: Uniformidade da textura
            - homogeneidade: Suavidade da textura
            - contraste_glcm: Contraste baseado em GLCM
            - correlacao: Correlação de pixels vizinhos
            - histograma_rgb: Características de cor
            - histograma_hsv: Características HSV
            - textura_dominante: Tipo predominante
        """
        if roi is None or roi.size == 0:
            return self._resultado_vazio()
        
        # Converte para escala de cinza
        if len(roi.shape) == 3:
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = roi.copy()
        
        # Cria máscara se temos contorno
        mask = self._criar_mascara(gray.shape, contorno) if contorno is not None else None
        
        # 1. Entropia (medida de aleatoriedade)
        entropia = self._calcular_entropia(gray, mask)
        
        # 2. GLCM (Gray-Level Co-occurrence Matrix)
        glcm_features = self._calcular_glcm(gray, mask)
        
        # 3. Histogramas multi-canal
        hist_rgb = self._analisar_histograma_rgb(roi, mask)
        hist_hsv = self._analisar_histograma_hsv(roi, mask)
        
        # 4. Análise de bordas (Canny)
        densidade_bordas = self._analisar_bordas(gray, mask)
        
        # 5. Análise de frequências (FFT)
        freq_features = self._analisar_frequencias(gray, mask)
        
        # 6. Classificação de textura dominante
        textura_dominante = self._classificar_textura(
            entropia, 
            glcm_features['homogeneidade'],
            densidade_bordas
        )
        
        return {
            'entropia': round(entropia, 3),
            'energia': round(glcm_features['energia'], 3),
            'homogeneidade': round(glcm_features['homogeneidade'], 3),
            'contraste_glcm': round(glcm_features['contraste'], 3),
            'correlacao': round(glcm_features['correlacao'], 3),
            'densidade_bordas': round(densidade_bordas, 3),
            'freq_dominante': round(freq_features['freq_dominante'], 3),
            'rugosidade': round(freq_features['rugosidade'], 3),
            'histograma_rgb': hist_rgb,
            'histograma_hsv': hist_hsv,
            'textura_dominante': textura_dominante
        }
    
    def _criar_mascara(self, shape: Tuple, contorno: np.ndarray) -> np.ndarray:
        """
        Cria máscara binária do contorno.
        
        Args:
            shape: Dimensões da imagem (height, width)
            contorno: Contorno do buraco
            
        Returns:
            Máscara binária (255 dentro, 0 fora)
        """
        mask = np.zeros(shape, dtype=np.uint8)
        cv2.drawContours(mask, [contorno], -1, 255, -1)
        return mask
    
    def _calcular_entropia(self, gray: np.ndarray, mask: np.ndarray = None) -> float:
        """
        Calcula entropia de Shannon da imagem.
        
        Entropia mede a quantidade de informação/desordem na textura.
        Alta entropia = textura complexa/irregular
        Baixa entropia = textura uniforme/lisa
        
        Args:
            gray: Imagem em escala de cinza
            mask: Máscara opcional
            
        Returns:
            Entropia (0-8 para 256 níveis)
        """
        # Extrai pixels da região de interesse
        if mask is not None:
            pixels = gray[mask == 255]
        else:
            pixels = gray.flatten()
        
        if len(pixels) == 0:
            return 0.0
        
        # Calcula histograma normalizado (probabilidades)
        hist, _ = np.histogram(pixels, bins=256, range=(0, 256))
        hist = hist / hist.sum()
        
        # Remove bins vazios
        hist = hist[hist > 0]
        
        # Calcula entropia: H = -Σ(p * log2(p))
        entropia = -np.sum(hist * np.log2(hist))
        
        return float(entropia)
    
    def _calcular_glcm(self, gray: np.ndarray, mask: np.ndarray = None) -> Dict[str, float]:
        """
        Calcula características da Gray-Level Co-occurrence Matrix (GLCM).
        
        GLCM analisa relação entre pixels vizinhos, capturando padrões espaciais.
        
        Args:
            gray: Imagem em escala de cinza
            mask: Máscara opcional
            
        Returns:
            Dict com: energia, homogeneidade, contraste, correlação
        """
        # Reduz níveis de cinza para 32 (performance)
        gray_reduced = (gray // 8).astype(np.uint8)
        
        # Inicializa acumuladores
        energia_total = 0
        homogeneidade_total = 0
        contraste_total = 0
        correlacao_total = 0
        num_glcm = 0
        
        # Calcula GLCM para cada ângulo
        for angle in self.glcm_angles:
            # Deslocamento baseado no ângulo
            dy = int(np.round(np.sin(angle)))
            dx = int(np.round(np.cos(angle)))
            
            # Calcula GLCM simples (co-ocorrência)
            glcm = self._compute_glcm_simple(gray_reduced, dx, dy, mask)
            
            # Normaliza
            if glcm.sum() > 0:
                glcm = glcm / glcm.sum()
            
            # Calcula features
            energia_total += self._glcm_energia(glcm)
            homogeneidade_total += self._glcm_homogeneidade(glcm)
            contraste_total += self._glcm_contraste(glcm)
            correlacao_total += self._glcm_correlacao(glcm)
            num_glcm += 1
        
        # Média entre todos os ângulos
        return {
            'energia': energia_total / num_glcm if num_glcm > 0 else 0,
            'homogeneidade': homogeneidade_total / num_glcm if num_glcm > 0 else 0,
            'contraste': contraste_total / num_glcm if num_glcm > 0 else 0,
            'correlacao': correlacao_total / num_glcm if num_glcm > 0 else 0
        }
    
    def _compute_glcm_simple(
        self, 
        img: np.ndarray, 
        dx: int, 
        dy: int, 
        mask: np.ndarray = None
    ) -> np.ndarray:
        """
        Calcula GLCM simples para deslocamento (dx, dy).
        
        Args:
            img: Imagem em níveis reduzidos (0-31)
            dx, dy: Deslocamento
            mask: Máscara opcional
            
        Returns:
            Matriz GLCM 32x32
        """
        levels = 32
        glcm = np.zeros((levels, levels), dtype=np.float64)
        
        h, w = img.shape
        
        for i in range(max(0, -dy), min(h, h - dy)):
            for j in range(max(0, -dx), min(w, w - dx)):
                # Verifica se está na máscara
                if mask is not None:
                    if mask[i, j] == 0 or mask[i + dy, j + dx] == 0:
                        continue
                
                # Co-ocorrência
                val1 = img[i, j]
                val2 = img[i + dy, j + dx]
                
                if val1 < levels and val2 < levels:
                    glcm[val1, val2] += 1
        
        return glcm
    
    def _glcm_energia(self, glcm: np.ndarray) -> float:
        """Energia (Angular Second Moment): uniformidade."""
        return float(np.sum(glcm ** 2))
    
    def _glcm_homogeneidade(self, glcm: np.ndarray) -> float:
        """Homogeneidade (Inverse Difference Moment): suavidade."""
        i, j = np.indices(glcm.shape)
        return float(np.sum(glcm / (1 + (i - j) ** 2)))
    
    def _glcm_contraste(self, glcm: np.ndarray) -> float:
        """Contraste: variação local."""
        i, j = np.indices(glcm.shape)
        return float(np.sum(glcm * (i - j) ** 2))
    
    def _glcm_correlacao(self, glcm: np.ndarray) -> float:
        """Correlação: dependência linear de pixels vizinhos."""
        i, j = np.indices(glcm.shape)
        
        # Médias
        mu_i = np.sum(i * glcm)
        mu_j = np.sum(j * glcm)
        
        # Desvios padrão
        sigma_i = np.sqrt(np.sum(glcm * (i - mu_i) ** 2))
        sigma_j = np.sqrt(np.sum(glcm * (j - mu_j) ** 2))
        
        if sigma_i == 0 or sigma_j == 0:
            return 0.0
        
        # Correlação
        corr = np.sum(glcm * (i - mu_i) * (j - mu_j)) / (sigma_i * sigma_j)
        return float(corr)
    
    def _analisar_histograma_rgb(
        self, 
        roi: np.ndarray, 
        mask: np.ndarray = None
    ) -> Dict[str, float]:
        """
        Analisa distribuição de cores RGB.
        
        Args:
            roi: Região colorida
            mask: Máscara opcional
            
        Returns:
            Média e desvio de cada canal
        """
        if len(roi.shape) != 3:
            return {'r_mean': 0, 'g_mean': 0, 'b_mean': 0}
        
        b, g, r = cv2.split(roi)
        
        if mask is not None:
            r_vals = r[mask == 255]
            g_vals = g[mask == 255]
            b_vals = b[mask == 255]
        else:
            r_vals = r.flatten()
            g_vals = g.flatten()
            b_vals = b.flatten()
        
        return {
            'r_mean': float(np.mean(r_vals)) if len(r_vals) > 0 else 0,
            'g_mean': float(np.mean(g_vals)) if len(g_vals) > 0 else 0,
            'b_mean': float(np.mean(b_vals)) if len(b_vals) > 0 else 0,
            'r_std': float(np.std(r_vals)) if len(r_vals) > 0 else 0,
            'g_std': float(np.std(g_vals)) if len(g_vals) > 0 else 0,
            'b_std': float(np.std(b_vals)) if len(b_vals) > 0 else 0
        }
    
    def _analisar_histograma_hsv(
        self, 
        roi: np.ndarray, 
        mask: np.ndarray = None
    ) -> Dict[str, float]:
        """
        Analisa distribuição HSV (Hue, Saturation, Value).
        
        Args:
            roi: Região colorida
            mask: Máscara opcional
            
        Returns:
            Média de matiz, saturação e valor
        """
        if len(roi.shape) != 3:
            return {'h_mean': 0, 's_mean': 0, 'v_mean': 0}
        
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        
        if mask is not None:
            h_vals = h[mask == 255]
            s_vals = s[mask == 255]
            v_vals = v[mask == 255]
        else:
            h_vals = h.flatten()
            s_vals = s.flatten()
            v_vals = v.flatten()
        
        return {
            'h_mean': float(np.mean(h_vals)) if len(h_vals) > 0 else 0,
            's_mean': float(np.mean(s_vals)) if len(s_vals) > 0 else 0,
            'v_mean': float(np.mean(v_vals)) if len(v_vals) > 0 else 0
        }
    
    def _analisar_bordas(self, gray: np.ndarray, mask: np.ndarray = None) -> float:
        """
        Calcula densidade de bordas usando Canny.
        
        Args:
            gray: Imagem em escala de cinza
            mask: Máscara opcional
            
        Returns:
            Porcentagem de pixels de borda (0-100)
        """
        # Detecta bordas
        edges = cv2.Canny(gray, 50, 150)
        
        # Aplica máscara se disponível
        if mask is not None:
            edges = cv2.bitwise_and(edges, edges, mask=mask)
            total_pixels = np.sum(mask == 255)
        else:
            total_pixels = edges.size
        
        # Calcula densidade
        edge_pixels = np.sum(edges > 0)
        densidade = (edge_pixels / total_pixels * 100) if total_pixels > 0 else 0
        
        return float(densidade)
    
    def _analisar_frequencias(
        self, 
        gray: np.ndarray, 
        mask: np.ndarray = None
    ) -> Dict[str, float]:
        """
        Analisa componentes de frequência usando FFT.
        
        Alta frequência = textura rugosa/detalhada
        Baixa frequência = textura lisa/uniforme
        
        Args:
            gray: Imagem em escala de cinza
            mask: Máscara opcional
            
        Returns:
            Frequência dominante e rugosidade
        """
        # FFT 2D
        f = np.fft.fft2(gray)
        fshift = np.fft.fftshift(f)
        magnitude = np.abs(fshift)
        
        # Centro da imagem (DC component)
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2
        
        # Remove componente DC
        magnitude[cy-2:cy+2, cx-2:cx+2] = 0
        
        # Calcula frequência dominante
        max_val = np.max(magnitude)
        max_pos = np.unravel_index(np.argmax(magnitude), magnitude.shape)
        
        # Distância do centro (frequência)
        freq_dominante = np.sqrt((max_pos[0] - cy)**2 + (max_pos[1] - cx)**2)
        
        # Rugosidade (energia em altas frequências)
        radius = min(h, w) // 4
        y, x = np.ogrid[:h, :w]
        mask_freq = ((y - cy)**2 + (x - cx)**2) > radius**2
        energia_alta = np.sum(magnitude[mask_freq])
        energia_total = np.sum(magnitude)
        
        rugosidade = (energia_alta / energia_total * 100) if energia_total > 0 else 0
        
        return {
            'freq_dominante': float(freq_dominante),
            'rugosidade': float(rugosidade)
        }
    
    def _classificar_textura(
        self, 
        entropia: float, 
        homogeneidade: float,
        densidade_bordas: float
    ) -> str:
        """
        Classifica tipo de textura baseado em métricas.
        
        Args:
            entropia: Medida de desordem
            homogeneidade: Medida de suavidade
            densidade_bordas: % de bordas
            
        Returns:
            'lisa', 'rugosa', 'irregular' ou 'complexa'
        """
        # Lisa: baixa entropia, alta homogeneidade, poucas bordas
        if entropia < 4.0 and homogeneidade > 0.7 and densidade_bordas < 10:
            return 'lisa'
        
        # Rugosa: entropia média, homogeneidade baixa, bordas moderadas
        elif 4.0 <= entropia < 6.0 and homogeneidade < 0.5 and densidade_bordas < 30:
            return 'rugosa'
        
        # Irregular: alta entropia, baixa homogeneidade, muitas bordas
        elif entropia >= 6.0 and homogeneidade < 0.3 and densidade_bordas >= 30:
            return 'irregular'
        
        # Complexa: outros casos
        else:
            return 'complexa'
    
    def _resultado_vazio(self) -> Dict[str, any]:
        """Retorna resultado vazio para casos de erro."""
        return {
            'entropia': 0.0,
            'energia': 0.0,
            'homogeneidade': 0.0,
            'contraste_glcm': 0.0,
            'correlacao': 0.0,
            'densidade_bordas': 0.0,
            'freq_dominante': 0.0,
            'rugosidade': 0.0,
            'histograma_rgb': {'r_mean': 0, 'g_mean': 0, 'b_mean': 0, 'r_std': 0, 'g_std': 0, 'b_std': 0},
            'histograma_hsv': {'h_mean': 0, 's_mean': 0, 'v_mean': 0},
            'textura_dominante': 'desconhecida'
        }
