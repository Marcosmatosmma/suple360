"""
Módulo de Otimização de Performance
====================================

Pipeline otimizado com multi-threading e processamento paralelo.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
import threading
import queue
import time
from typing import Optional, Callable, Any


class PerformanceOptimizer:
    """
    Otimizador de performance para pipeline de detecção.
    
    Funcionalidades:
    - Multi-threading para I/O e processamento
    - Fila de frames para processamento assíncrono
    - Adaptive frame skipping
    - Métricas de performance em tempo real
    """
    
    def __init__(
        self, 
        process_func: Callable,
        max_queue_size: int = 3,
        num_workers: int = 2
    ):
        """
        Inicializa otimizador.
        
        Args:
            process_func: Função de processamento (recebe frame, retorna resultado)
            max_queue_size: Tamanho máximo da fila de frames
            num_workers: Número de threads de processamento
        """
        self.process_func = process_func
        self.max_queue_size = max_queue_size
        self.num_workers = num_workers
        
        # Filas
        self.input_queue = queue.Queue(maxsize=max_queue_size)
        self.output_queue = queue.Queue()
        
        # Controle de threads
        self.workers = []
        self.running = False
        self.lock = threading.Lock()
        
        # Métricas
        self.frames_processed = 0
        self.frames_skipped = 0
        self.total_processing_time = 0.0
        self.start_time = None
    
    def start(self):
        """Inicia workers de processamento."""
        self.running = True
        self.start_time = time.time()
        
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"Worker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        print(f"✅ Pipeline iniciado com {self.num_workers} workers")
    
    def stop(self):
        """Para workers de processamento."""
        self.running = False
        
        # Aguarda workers terminarem
        for worker in self.workers:
            worker.join(timeout=2.0)
        
        self.workers = []
        print("🛑 Pipeline parado")
    
    def _worker_loop(self):
        """Loop principal do worker."""
        while self.running:
            try:
                # Pega frame da fila (timeout 0.5s)
                frame_data = self.input_queue.get(timeout=0.5)
                
                if frame_data is None:
                    break
                
                frame, frame_id = frame_data
                
                # Processa frame
                start_time = time.time()
                result = self.process_func(frame)
                processing_time = time.time() - start_time
                
                # Coloca resultado na fila
                self.output_queue.put((frame_id, result, processing_time))
                
                # Atualiza métricas
                with self.lock:
                    self.frames_processed += 1
                    self.total_processing_time += processing_time
                
                self.input_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Erro no worker: {e}")
    
    def submit_frame(self, frame: np.ndarray, frame_id: int) -> bool:
        """
        Submete frame para processamento.
        
        Args:
            frame: Frame para processar
            frame_id: ID único do frame
            
        Returns:
            True se aceito, False se fila cheia (frame pulado)
        """
        try:
            self.input_queue.put((frame, frame_id), block=False)
            return True
        except queue.Full:
            # Fila cheia: pula frame
            with self.lock:
                self.frames_skipped += 1
            return False
    
    def get_result(self, timeout: float = 0.1) -> Optional[tuple]:
        """
        Pega resultado processado.
        
        Args:
            timeout: Timeout em segundos
            
        Returns:
            Tuple (frame_id, result, processing_time) ou None
        """
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_metrics(self) -> dict:
        """
        Retorna métricas de performance.
        
        Returns:
            Dict com métricas
        """
        with self.lock:
            elapsed_time = time.time() - self.start_time if self.start_time else 1.0
            total_frames = self.frames_processed + self.frames_skipped
            
            fps = self.frames_processed / elapsed_time if elapsed_time > 0 else 0
            avg_processing_time = (
                self.total_processing_time / self.frames_processed 
                if self.frames_processed > 0 else 0
            )
            skip_rate = (
                self.frames_skipped / total_frames * 100 
                if total_frames > 0 else 0
            )
            
            return {
                'frames_processed': self.frames_processed,
                'frames_skipped': self.frames_skipped,
                'total_frames': total_frames,
                'fps': round(fps, 2),
                'avg_processing_time_ms': round(avg_processing_time * 1000, 1),
                'skip_rate': round(skip_rate, 1),
                'queue_size': self.input_queue.qsize(),
                'elapsed_time': round(elapsed_time, 1)
            }


class AdaptiveFrameSkipper:
    """
    Pula frames adaptativamente baseado em carga de processamento.
    
    Mantém FPS alvo pulando frames quando necessário.
    """
    
    def __init__(self, target_fps: int = 10):
        """
        Inicializa frame skipper.
        
        Args:
            target_fps: FPS alvo (ex: 10 FPS)
        """
        self.target_fps = target_fps
        self.min_frame_interval = 1.0 / target_fps
        
        self.last_process_time = 0
        self.frames_total = 0
        self.frames_skipped = 0
    
    def should_process(self) -> bool:
        """
        Decide se deve processar frame atual.
        
        Returns:
            True se deve processar, False para pular
        """
        current_time = time.time()
        self.frames_total += 1
        
        # Verifica intervalo mínimo
        if current_time - self.last_process_time >= self.min_frame_interval:
            self.last_process_time = current_time
            return True
        else:
            self.frames_skipped += 1
            return False
    
    def get_stats(self) -> dict:
        """Retorna estatísticas."""
        skip_rate = (
            self.frames_skipped / self.frames_total * 100 
            if self.frames_total > 0 else 0
        )
        
        return {
            'target_fps': self.target_fps,
            'frames_skipped': self.frames_skipped,
            'frames_processed': self.frames_total - self.frames_skipped,
            'skip_rate': round(skip_rate, 1)
        }
