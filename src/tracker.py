import numpy as np
import time


class BuracoTracker:
    """
    Rastreia buracos entre frames consecutivos para evitar detecções duplicadas.
    
    Funcionalidade:
    - Compara buracos detectados com buracos já rastreados
    - Identifica se é o mesmo buraco (baseado em posição e tempo)
    - Mantém histórico de buracos únicos
    - Evita salvar o mesmo buraco múltiplas vezes no banco
    """
    
    def __init__(self, iou_threshold=0.3, max_age_seconds=5.0):
        """
        Inicializa o tracker de buracos.
        
        Args:
            iou_threshold: Limiar de IoU para considerar mesmo buraco (0-1)
            max_age_seconds: Tempo máximo para manter buraco sem atualização
        """
        self.tracked_buracos = []  # Lista de buracos rastreados
        self.iou_threshold = iou_threshold
        self.max_age_seconds = max_age_seconds
        self.next_id = 1  # Próximo ID a ser atribuído
    
    def update(self, detections):
        """
        Atualiza o tracker com novas detecções.
        
        Args:
            detections: Lista de detecções [(x1, y1, x2, y2, conf, dist_m, width_m), ...]
        
        Returns:
            tuple: (novos_buracos, buracos_atualizados)
                - novos_buracos: Lista de buracos detectados pela primeira vez
                - buracos_atualizados: Lista de buracos que já existiam
        """
        current_time = time.time()
        
        # Remove buracos antigos (que saíram do campo de visão)
        self._remove_old_tracks(current_time)
        
        if not detections:
            return [], []
        
        novos_buracos = []
        buracos_atualizados = []
        
        # Para cada detecção, tenta associar com buraco existente
        for detection in detections:
            bbox_det = detection[:4]  # (x1, y1, x2, y2)
            
            # Procura buraco correspondente nos rastreados
            matched_track = self._find_matching_track(bbox_det, current_time)
            
            if matched_track is None:
                # Novo buraco detectado!
                track_id = self._create_new_track(detection, current_time)
                novos_buracos.append({
                    'track_id': track_id,
                    'detection': detection,
                    'is_new': True
                })
            else:
                # Buraco já conhecido, apenas atualiza
                self._update_track(matched_track, detection, current_time)
                buracos_atualizados.append({
                    'track_id': matched_track['id'],
                    'detection': detection,
                    'is_new': False,
                    'detection_count': matched_track['count']
                })
        
        return novos_buracos, buracos_atualizados
    
    def _find_matching_track(self, bbox, current_time):
        """
        Encontra track existente que corresponde ao bbox fornecido.
        
        Args:
            bbox: Tuple (x1, y1, x2, y2) da nova detecção
            current_time: Timestamp atual
        
        Returns:
            dict ou None: Track correspondente ou None se não encontrou
        """
        best_match = None
        best_iou = self.iou_threshold
        
        for track in self.tracked_buracos:
            # Ignora tracks muito antigos
            if current_time - track['last_seen'] > self.max_age_seconds:
                continue
            
            # Calcula IoU (Intersection over Union)
            iou = self._calculate_iou(bbox, track['bbox'])
            
            # Se IoU é maior que threshold, é candidato a match
            if iou > best_iou:
                best_iou = iou
                best_match = track
        
        return best_match
    
    def _calculate_iou(self, bbox1, bbox2):
        """
        Calcula IoU (Intersection over Union) entre dois bounding boxes.
        
        IoU = Área de Interseção / Área de União
        Valores: 0 (sem overlap) a 1 (boxes idênticos)
        
        Args:
            bbox1: Tuple (x1, y1, x2, y2)
            bbox2: Tuple (x1, y1, x2, y2)
        
        Returns:
            float: Valor de IoU entre 0 e 1
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Coordenadas da interseção
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        # Calcula área de interseção
        if x2_i < x1_i or y2_i < y1_i:
            intersection = 0  # Não há interseção
        else:
            intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calcula áreas individuais
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        
        # Calcula união
        union = area1 + area2 - intersection
        
        if union == 0:
            return 0
        
        return intersection / union
    
    def _create_new_track(self, detection, current_time):
        """
        Cria um novo track para um buraco detectado pela primeira vez.
        
        Args:
            detection: Tuple (x1, y1, x2, y2, conf, dist_m, width_m)
            current_time: Timestamp atual
        
        Returns:
            int: ID do novo track criado
        """
        track_id = self.next_id
        self.next_id += 1
        
        bbox = detection[:4]
        
        new_track = {
            'id': track_id,
            'bbox': bbox,
            'first_seen': current_time,
            'last_seen': current_time,
            'count': 1,  # Número de vezes que foi detectado
            'confidence_avg': detection[4],  # Confiança média
            'last_detection': detection
        }
        
        self.tracked_buracos.append(new_track)
        return track_id
    
    def _update_track(self, track, detection, current_time):
        """
        Atualiza um track existente com nova detecção.
        
        Args:
            track: Dict do track a atualizar
            detection: Tuple (x1, y1, x2, y2, conf, dist_m, width_m)
            current_time: Timestamp atual
        """
        bbox = detection[:4]
        conf = detection[4]
        
        # Atualiza bbox (média ponderada com posição anterior)
        alpha = 0.7  # Peso da nova detecção
        track['bbox'] = self._smooth_bbox(track['bbox'], bbox, alpha)
        
        # Atualiza timestamp
        track['last_seen'] = current_time
        
        # Incrementa contador
        track['count'] += 1
        
        # Atualiza confiança média
        track['confidence_avg'] = (
            (track['confidence_avg'] * (track['count'] - 1) + conf) / track['count']
        )
        
        # Guarda última detecção
        track['last_detection'] = detection
    
    def _smooth_bbox(self, old_bbox, new_bbox, alpha):
        """
        Suaviza transição entre bboxes usando média ponderada.
        
        Args:
            old_bbox: Bbox anterior (x1, y1, x2, y2)
            new_bbox: Bbox novo (x1, y1, x2, y2)
            alpha: Peso do novo bbox (0-1)
        
        Returns:
            tuple: Bbox suavizado
        """
        smoothed = []
        for old, new in zip(old_bbox, new_bbox):
            smoothed.append(int(alpha * new + (1 - alpha) * old))
        return tuple(smoothed)
    
    def _remove_old_tracks(self, current_time):
        """
        Remove tracks que não foram atualizados há muito tempo.
        
        Args:
            current_time: Timestamp atual
        """
        self.tracked_buracos = [
            track for track in self.tracked_buracos
            if current_time - track['last_seen'] <= self.max_age_seconds
        ]
    
    def get_statistics(self):
        """
        Retorna estatísticas do tracker.
        
        Returns:
            dict: Estatísticas atuais
        """
        if not self.tracked_buracos:
            return {
                'total_tracks': 0,
                'active_tracks': 0,
                'avg_detection_count': 0
            }
        
        current_time = time.time()
        active = sum(
            1 for t in self.tracked_buracos
            if current_time - t['last_seen'] <= 1.0
        )
        
        avg_count = np.mean([t['count'] for t in self.tracked_buracos])
        
        return {
            'total_tracks': len(self.tracked_buracos),
            'active_tracks': active,
            'avg_detection_count': round(avg_count, 1)
        }
    
    def reset(self):
        """Reseta o tracker, removendo todos os tracks."""
        self.tracked_buracos = []
        self.next_id = 1
