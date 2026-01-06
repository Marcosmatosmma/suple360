"""
Módulo de Classificação de Tipo de Dano
========================================

Classifica tipo de dano na via baseado em características visuais:
- Buraco circular/irregular
- Rachadura linear
- Erosão superficial
- Dano combinado

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from typing import Dict, Tuple


class DamageClassifier:
    """
    Classificador de tipo de dano em vias.
    
    Analisa forma, textura e padrões para identificar:
    - buraco_circular: Buraco compacto e arredondado
    - buraco_irregular: Buraco com forma irregular
    - rachadura: Dano linear/alongado
    - erosao: Dano superficial disperso
    - combinado: Múltiplos tipos de dano
    """
    
    def __init__(self):
        """Inicializa o classificador de danos."""
        # Thresholds para classificação
        self.CIRCULAR_THRESHOLD = 0.65      # Circularidade mínima para circular
        self.RACHADURA_ASPECT_MIN = 3.0     # Aspect ratio mínimo para rachadura
        self.EROSAO_AREA_MAX = 0.08         # Área máxima (m²) para erosão
        self.IRREGULAR_CONVEX_MAX = 0.60    # Convexidade máxima para irregular
    
    def classificar_dano(
        self,
        roi: np.ndarray,
        contorno: np.ndarray,
        geometria: Dict,
        textura_avancada: Dict,
        dimensoes_reais: Dict
    ) -> Dict[str, any]:
        """
        Classifica o tipo de dano baseado em múltiplas características.
        
        Args:
            roi: Região de interesse (imagem do buraco)
            contorno: Contorno do buraco
            geometria: Características geométricas (do opencv_analyzer)
            textura_avancada: Análise de textura (do texture_analyzer)
            dimensoes_reais: Dimensões em metros
            
        Returns:
            Dict com:
            - tipo_dano: Classificação principal
            - confianca: Confiança da classificação (0-100)
            - caracteristicas: Características que levaram à classificação
            - tipo_secundario: Tipo secundário se houver
        """
        # Extrai métricas relevantes
        circularidade = geometria.get('circularidade', 0)
        aspect_ratio = geometria.get('aspect_ratio', 1)
        convexidade = geometria.get('convexidade', 1)
        area_m2 = dimensoes_reais.get('area_m2', 0)
        
        entropia = textura_avancada.get('entropia', 0)
        densidade_bordas = textura_avancada.get('densidade_bordas', 0)
        homogeneidade = textura_avancada.get('homogeneidade', 0)
        
        # Análise adicional do contorno
        contorno_features = self._analisar_contorno(contorno)
        
        # Análise de esqueleto (para rachaduras)
        skeleton_features = self._analisar_esqueleto(roi, contorno)
        
        # Score para cada tipo
        scores = {
            'buraco_circular': self._score_buraco_circular(
                circularidade, convexidade, area_m2, homogeneidade
            ),
            'buraco_irregular': self._score_buraco_irregular(
                circularidade, convexidade, entropia, densidade_bordas
            ),
            'rachadura': self._score_rachadura(
                aspect_ratio, skeleton_features, contorno_features
            ),
            'erosao': self._score_erosao(
                area_m2, homogeneidade, densidade_bordas
            )
        }
        
        # Tipo dominante
        tipo_principal = max(scores, key=scores.get)
        confianca_principal = scores[tipo_principal]
        
        # Verifica se há tipo secundário (score > 50 e diferença < 20)
        scores_ordenados = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        tipo_secundario = None
        
        if len(scores_ordenados) > 1:
            segundo_tipo, segundo_score = scores_ordenados[1]
            if segundo_score > 50 and (confianca_principal - segundo_score) < 20:
                tipo_secundario = segundo_tipo
                tipo_principal = 'combinado'
        
        return {
            'tipo_dano': tipo_principal,
            'confianca': round(confianca_principal, 1),
            'tipo_secundario': tipo_secundario,
            'scores_detalhados': {k: round(v, 1) for k, v in scores.items()},
            'caracteristicas': self._gerar_caracteristicas(
                tipo_principal, geometria, textura_avancada
            )
        }
    
    def _analisar_contorno(self, contorno: np.ndarray) -> Dict[str, float]:
        """
        Analisa características do contorno.
        
        Args:
            contorno: Contorno do buraco
            
        Returns:
            Número de vértices e solidez
        """
        # Aproxima contorno por polígono
        epsilon = 0.02 * cv2.arcLength(contorno, True)
        approx = cv2.approxPolyDP(contorno, epsilon, True)
        num_vertices = len(approx)
        
        # Solidez (área / área do convex hull)
        area = cv2.contourArea(contorno)
        hull = cv2.convexHull(contorno)
        hull_area = cv2.contourArea(hull)
        solidez = area / hull_area if hull_area > 0 else 0
        
        return {
            'num_vertices': num_vertices,
            'solidez': float(solidez)
        }
    
    def _analisar_esqueleto(
        self, 
        roi: np.ndarray, 
        contorno: np.ndarray
    ) -> Dict[str, float]:
        """
        Analisa esqueleto (skeleton) da região para detectar estruturas lineares.
        
        Rachaduras têm esqueleto alongado e fino.
        
        Args:
            roi: Região de interesse
            contorno: Contorno do buraco
            
        Returns:
            Comprimento do esqueleto e razão
        """
        # Cria máscara binária
        mask = np.zeros(roi.shape[:2], dtype=np.uint8)
        cv2.drawContours(mask, [contorno], -1, 255, -1)
        
        # Esqueletização (thinning)
        skeleton = cv2.ximgproc.thinning(mask) if hasattr(cv2, 'ximgproc') else mask
        
        # Comprimento do esqueleto
        skeleton_length = np.sum(skeleton > 0)
        area = np.sum(mask > 0)
        
        # Razão comprimento/área (alto para rachaduras)
        razao_skeleton = skeleton_length / area if area > 0 else 0
        
        return {
            'skeleton_length': float(skeleton_length),
            'skeleton_ratio': float(razao_skeleton)
        }
    
    def _score_buraco_circular(
        self,
        circularidade: float,
        convexidade: float,
        area_m2: float,
        homogeneidade: float
    ) -> float:
        """
        Calcula score para buraco circular.
        
        Critérios:
        - Alta circularidade (> 0.65)
        - Alta convexidade (> 0.80)
        - Área moderada (0.01-0.3 m²)
        - Textura relativamente homogênea
        """
        score = 0
        
        # Circularidade (peso 40%)
        if circularidade > 0.80:
            score += 40
        elif circularidade > 0.65:
            score += 30
        elif circularidade > 0.50:
            score += 15
        
        # Convexidade (peso 30%)
        if convexidade > 0.85:
            score += 30
        elif convexidade > 0.70:
            score += 20
        
        # Área razoável (peso 15%)
        if area_m2 and 0.01 <= area_m2 <= 0.3:
            score += 15
        
        # Homogeneidade (peso 15%)
        if homogeneidade > 0.5:
            score += 15
        elif homogeneidade > 0.3:
            score += 10
        
        return min(100, score)
    
    def _score_buraco_irregular(
        self,
        circularidade: float,
        convexidade: float,
        entropia: float,
        densidade_bordas: float
    ) -> float:
        """
        Calcula score para buraco irregular.
        
        Critérios:
        - Baixa circularidade (< 0.60)
        - Baixa convexidade (< 0.70)
        - Alta entropia (textura complexa)
        - Muitas bordas irregulares
        """
        score = 0
        
        # Baixa circularidade (peso 30%)
        if circularidade < 0.40:
            score += 30
        elif circularidade < 0.60:
            score += 20
        
        # Baixa convexidade (peso 30%)
        if convexidade < 0.50:
            score += 30
        elif convexidade < 0.70:
            score += 20
        
        # Alta entropia (peso 25%)
        if entropia > 6.0:
            score += 25
        elif entropia > 5.0:
            score += 15
        
        # Densidade de bordas (peso 15%)
        if densidade_bordas > 30:
            score += 15
        elif densidade_bordas > 20:
            score += 10
        
        return min(100, score)
    
    def _score_rachadura(
        self,
        aspect_ratio: float,
        skeleton_features: Dict,
        contorno_features: Dict
    ) -> float:
        """
        Calcula score para rachadura.
        
        Critérios:
        - Alto aspect ratio (> 3.0)
        - Esqueleto alongado
        - Forma fina e linear
        """
        score = 0
        
        # Aspect ratio alto (peso 40%)
        if aspect_ratio > 5.0:
            score += 40
        elif aspect_ratio > 3.0:
            score += 30
        elif aspect_ratio > 2.0:
            score += 15
        
        # Razão do esqueleto (peso 35%)
        skeleton_ratio = skeleton_features.get('skeleton_ratio', 0)
        if skeleton_ratio > 0.8:
            score += 35
        elif skeleton_ratio > 0.6:
            score += 25
        
        # Solidez (rachaduras têm alta solidez) (peso 25%)
        solidez = contorno_features.get('solidez', 0)
        if solidez > 0.9:
            score += 25
        elif solidez > 0.8:
            score += 15
        
        return min(100, score)
    
    def _score_erosao(
        self,
        area_m2: float,
        homogeneidade: float,
        densidade_bordas: float
    ) -> float:
        """
        Calcula score para erosão superficial.
        
        Critérios:
        - Área pequena/dispersa (< 0.08 m²)
        - Baixa homogeneidade (textura variada)
        - Bordas difusas (baixa densidade)
        """
        score = 0
        
        # Área pequena (peso 40%)
        if area_m2 and area_m2 < 0.05:
            score += 40
        elif area_m2 and area_m2 < 0.08:
            score += 25
        
        # Baixa homogeneidade (peso 30%)
        if homogeneidade < 0.3:
            score += 30
        elif homogeneidade < 0.5:
            score += 20
        
        # Bordas difusas (peso 30%)
        if densidade_bordas < 15:
            score += 30
        elif densidade_bordas < 25:
            score += 20
        
        return min(100, score)
    
    def _gerar_caracteristicas(
        self,
        tipo: str,
        geometria: Dict,
        textura: Dict
    ) -> str:
        """
        Gera descrição textual das características.
        
        Args:
            tipo: Tipo de dano classificado
            geometria: Dados geométricos
            textura: Dados de textura
            
        Returns:
            Descrição em português
        """
        circ = geometria.get('circularidade', 0)
        asp = geometria.get('aspect_ratio', 1)
        entr = textura.get('entropia', 0)
        
        if tipo == 'buraco_circular':
            return f"Buraco compacto (circ={circ:.2f}), forma regular"
        elif tipo == 'buraco_irregular':
            return f"Buraco irregular (circ={circ:.2f}), bordas complexas"
        elif tipo == 'rachadura':
            return f"Estrutura linear (asp={asp:.2f}), alongada"
        elif tipo == 'erosao':
            return f"Dano superficial disperso, área pequena"
        else:
            return f"Dano combinado, múltiplas características"
