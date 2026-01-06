import cv2
import numpy as np
from depth_estimator import DepthEstimator
from texture_analyzer import TextureAnalyzer
from damage_classifier import DamageClassifier


class OpenCVAnalyzer:
    """
    Analisa geometria e características de buracos detectados usando OpenCV.
    
    Este módulo extrai informações detalhadas sobre cada buraco:
    - Dimensões físicas (área, perímetro, largura, altura)
    - Geometria (circularidade, convexidade, orientação)
    - Formato (aspect ratio, elipse ajustada)
    """
    
    def __init__(self):
        """Inicializa o analisador OpenCV."""
        self.depth_estimator = DepthEstimator()
        self.texture_analyzer = TextureAnalyzer()
        self.damage_classifier = DamageClassifier()
    
    def analisar_buraco(self, frame, bbox, distancia_m=None):
        """
        Analisa um buraco detectado e extrai suas características geométricas.
        
        Args:
            frame: Imagem completa (numpy array BGR)
            bbox: Tuple (x1, y1, x2, y2) - coordenadas do bounding box
            distancia_m: Distância do buraco em metros (do LIDAR)
        
        Returns:
            dict: Dicionário com todas as medidas e características
        """
        x1, y1, x2, y2 = bbox
        
        # Extrai região do buraco
        roi = frame[y1:y2, x1:x2]
        
        if roi.size == 0:
            return self._get_default_analysis()
        
        # Dimensões em pixels
        largura_px = x2 - x1
        altura_px = y2 - y1
        
        # Prepara imagem para análise
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detecta contornos
        contorno = self._extrair_contorno(blurred)
        
        # Análise geométrica
        geometria = self._analisar_geometria(contorno, largura_px, altura_px)
        
        # Análise de textura
        textura = self._analisar_textura(gray)
        
        # Análise de textura avançada (Fase 4)
        textura_avancada = self.texture_analyzer.analisar_textura_avancada(roi, contorno)
        
        # Análise de profundidade (Fase 3)
        profundidade = self.depth_estimator.estimar_profundidade(
            roi, distancia_m if distancia_m else 2.0, contorno
        )
        
        # Conversão para medidas reais (se temos distância do LIDAR)
        dimensoes_reais = self._converter_para_metros(
            geometria, distancia_m, largura_px, altura_px
        )
        
        # Classificação de severidade
        severidade = self._classificar_severidade(dimensoes_reais, geometria)
        
        # Classificação de tipo de dano (Fase 4)
        tipo_dano = self.damage_classifier.classificar_dano(
            roi, contorno, 
            {'circularidade': geometria['circularidade'],
             'aspect_ratio': geometria['aspect_ratio'],
             'convexidade': geometria['convexidade']},
            textura_avancada,
            dimensoes_reais
        )
        
        return {
            'dimensoes_pixels': {
                'largura_px': largura_px,
                'altura_px': altura_px,
                'area_px': geometria['area_px'],
                'perimetro_px': geometria['perimetro_px']
            },
            'dimensoes_reais': dimensoes_reais,
            'geometria': {
                'aspect_ratio': geometria['aspect_ratio'],
                'circularidade': geometria['circularidade'],
                'convexidade': geometria['convexidade'],
                'orientacao_deg': geometria['orientacao_deg'],
                'elipse_eixo_maior': geometria['elipse_eixo_maior'],
                'elipse_eixo_menor': geometria['elipse_eixo_menor']
            },
            'textura': textura,
            'textura_avancada': textura_avancada,
            'profundidade': profundidade,
            'tipo_dano': tipo_dano,
            'classificacao': severidade
        }
    
    def _extrair_contorno(self, gray_image):
        """
        Extrai o contorno principal da região do buraco.
        
        Args:
            gray_image: Imagem em escala de cinza
            
        Returns:
            numpy.ndarray: Contorno principal encontrado
        """
        # Binarização adaptativa (melhor para iluminação variável)
        thresh = cv2.adaptiveThreshold(
            gray_image, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            11, 2
        )
        
        # Encontra contornos
        contours, _ = cv2.findContours(
            thresh,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            # Se não encontrou contornos, cria retângulo da ROI
            h, w = gray_image.shape
            return np.array([
                [[0, 0]], [[w, 0]], [[w, h]], [[0, h]]
            ], dtype=np.int32)
        
        # Retorna o maior contorno
        return max(contours, key=cv2.contourArea)
    
    def _analisar_geometria(self, contorno, largura_px, altura_px):
        """
        Calcula métricas geométricas do contorno.
        
        Args:
            contorno: Contorno OpenCV
            largura_px: Largura do bbox em pixels
            altura_px: Altura do bbox em pixels
            
        Returns:
            dict: Métricas geométricas calculadas
        """
        # Área e perímetro
        area_px = cv2.contourArea(contorno)
        perimetro_px = cv2.arcLength(contorno, True)
        
        # Evita divisão por zero
        if perimetro_px == 0:
            perimetro_px = 1
        if area_px == 0:
            area_px = 1
        
        # Circularidade (0-1, sendo 1 = círculo perfeito)
        # Fórmula: 4π × área / perímetro²
        circularidade = min(1.0, (4 * np.pi * area_px) / (perimetro_px ** 2))
        
        # Aspect ratio (proporção largura/altura)
        aspect_ratio = largura_px / max(1, altura_px)
        
        # Convexidade (quão irregular é o contorno)
        hull = cv2.convexHull(contorno)
        hull_area = cv2.contourArea(hull)
        convexidade = area_px / max(1, hull_area) if hull_area > 0 else 0
        
        # Orientação e elipse ajustada
        orientacao_deg = 0
        eixo_maior = largura_px
        eixo_menor = altura_px
        
        if len(contorno) >= 5:
            try:
                ellipse = cv2.fitEllipse(contorno)
                (cx, cy), (MA, ma), orientacao_deg = ellipse
                eixo_maior = max(MA, ma)
                eixo_menor = min(MA, ma)
            except:
                pass
        
        return {
            'area_px': area_px,
            'perimetro_px': perimetro_px,
            'circularidade': round(circularidade, 3),
            'aspect_ratio': round(aspect_ratio, 2),
            'convexidade': round(convexidade, 3),
            'orientacao_deg': round(orientacao_deg, 1),
            'elipse_eixo_maior': round(eixo_maior, 1),
            'elipse_eixo_menor': round(eixo_menor, 1)
        }
    
    def _analisar_textura(self, gray_image):
        """
        Analisa características de textura da região do buraco.
        
        Args:
            gray_image: Imagem em escala de cinza
            
        Returns:
            dict: Métricas de textura
        """
        # Intensidade média
        intensidade_media = np.mean(gray_image)
        
        # Desvio padrão (variação de intensidade)
        desvio_padrao = np.std(gray_image)
        
        # Contraste (diferença entre max e min normalizada)
        contraste = (np.max(gray_image) - np.min(gray_image)) / 255.0
        
        return {
            'intensidade_media': round(intensidade_media, 1),
            'desvio_padrao': round(desvio_padrao, 1),
            'contraste': round(contraste, 3)
        }
    
    def _converter_para_metros(self, geometria, distancia_m, largura_px, altura_px):
        """
        Converte medidas de pixels para metros usando distância do LIDAR.
        
        Args:
            geometria: Dict com medidas em pixels
            distancia_m: Distância em metros (do LIDAR)
            largura_px: Largura em pixels
            altura_px: Altura em pixels
            
        Returns:
            dict: Dimensões convertidas para metros
        """
        if distancia_m is None or distancia_m <= 0:
            return {
                'largura_m': None,
                'altura_m': None,
                'area_m2': None,
                'perimetro_m': None
            }
        
        # Estimativa de escala: pixels por metro
        # Assume FOV de 70° e usa trigonometria básica
        # largura_real = 2 × distância × tan(FOV/2)
        fov_rad = np.radians(70.0)
        largura_real_m = 2 * distancia_m * np.tan(fov_rad / 2)
        
        # Fator de conversão: metros por pixel
        meters_per_pixel = largura_real_m / max(1, largura_px)
        
        # Converte dimensões
        largura_m = largura_px * meters_per_pixel
        altura_m = altura_px * meters_per_pixel
        area_m2 = geometria['area_px'] * (meters_per_pixel ** 2)
        perimetro_m = geometria['perimetro_px'] * meters_per_pixel
        
        return {
            'largura_m': round(largura_m, 3),
            'altura_m': round(altura_m, 3),
            'area_m2': round(area_m2, 4),
            'perimetro_m': round(perimetro_m, 3)
        }
    
    def _classificar_severidade(self, dimensoes_reais, geometria):
        """
        Classifica a severidade do buraco baseado em suas características.
        
        Critérios:
        - Leve: área < 0.05 m² E circular
        - Médio: área 0.05-0.15 m² OU irregular
        - Grave: área > 0.15 m² OU muito irregular
        
        Args:
            dimensoes_reais: Dict com medidas em metros
            geometria: Dict com características geométricas
            
        Returns:
            dict: Classificação de severidade
        """
        area_m2 = dimensoes_reais.get('area_m2')
        circularidade = geometria.get('circularidade', 0)
        
        if area_m2 is None:
            return {
                'severidade': 'desconhecida',
                'necessita_reparo': True,
                'prioridade': 'media'
            }
        
        # Critérios de classificação
        if area_m2 < 0.05 and circularidade > 0.7:
            severidade = 'leve'
            prioridade = 'baixa'
            necessita_reparo = False
        elif area_m2 > 0.15 or circularidade < 0.4:
            severidade = 'grave'
            prioridade = 'alta'
            necessita_reparo = True
        else:
            severidade = 'media'
            prioridade = 'media'
            necessita_reparo = True
        
        return {
            'severidade': severidade,
            'necessita_reparo': necessita_reparo,
            'prioridade': prioridade
        }
    
    def _get_default_analysis(self):
        """
        Retorna análise padrão quando não é possível analisar o buraco.
        
        Returns:
            dict: Estrutura padrão com valores None
        """
        return {
            'dimensoes_pixels': {
                'largura_px': 0,
                'altura_px': 0,
                'area_px': 0,
                'perimetro_px': 0
            },
            'dimensoes_reais': {
                'largura_m': None,
                'altura_m': None,
                'area_m2': None,
                'perimetro_m': None
            },
            'geometria': {
                'aspect_ratio': 0,
                'circularidade': 0,
                'convexidade': 0,
                'orientacao_deg': 0,
                'elipse_eixo_maior': 0,
                'elipse_eixo_menor': 0
            },
            'textura': {
                'intensidade_media': 0,
                'desvio_padrao': 0,
                'contraste': 0
            },
            'textura_avancada': {
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
            },
            'profundidade': {
                'gradiente_medio': 0.0,
                'intensidade_sombra': 0.0,
                'variacao_intensidade': 0.0,
                'profundidade_score': 0.0,
                'profundidade_cm': 0.0,
                'classificacao': 'raso'
            },
            'tipo_dano': {
                'tipo_dano': 'desconhecido',
                'confianca': 0.0,
                'tipo_secundario': None,
                'scores_detalhados': {},
                'caracteristicas': ''
            },
            'classificacao': {
                'severidade': 'desconhecida',
                'necessita_reparo': True,
                'prioridade': 'media'
            }
        }
