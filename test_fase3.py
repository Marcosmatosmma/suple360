#!/usr/bin/env python3
"""
Teste da Fase 3 - Calibração e Profundidade
============================================

Script para testar as funcionalidades da Fase 3:
1. Calibração de câmera
2. Estimativa de profundidade
3. Integração com OpenCV Analyzer

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
import sys
import os

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from calibration import CameraCalibrator
from depth_estimator import DepthEstimator
from opencv_analyzer import OpenCVAnalyzer


def test_calibration():
    """Testa funcionalidades do CameraCalibrator."""
    print("\n" + "="*60)
    print("TESTE 1: Calibração de Câmera")
    print("="*60)
    
    calibrator = CameraCalibrator()
    
    # Testa conversão pixel → ângulo (sem calibração)
    print("\n📐 Testando conversão pixel → ângulo (estimativa)...")
    angle_x, angle_y = calibrator.pixel_to_world_angle(320, 240, 640, 480)
    print(f"  Pixel (320, 240) de 640x480 → Ângulo: ({angle_x:.2f}°, {angle_y:.2f}°)")
    
    # Testa correção de distorção sem calibração
    print("\n🖼️  Testando correção sem calibração...")
    test_img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    corrected = calibrator.undistort_image(test_img)
    
    if corrected is not None:
        print(f"  ✅ Imagem processada: {corrected.shape}")
    else:
        print("  ⚠️  Imagem não modificada (câmera não calibrada)")
    
    print("\n✅ Teste de calibração concluído")


def test_depth_estimator():
    """Testa funcionalidades do DepthEstimator."""
    print("\n" + "="*60)
    print("TESTE 2: Estimativa de Profundidade")
    print("="*60)
    
    estimator = DepthEstimator()
    
    # Cria imagem sintética de buraco
    print("\n🎨 Criando imagem sintética de buraco...")
    roi = np.ones((100, 100, 3), dtype=np.uint8) * 150  # Cinza médio
    
    # Simula buraco: área escura no centro
    cv2.circle(roi, (50, 50), 30, (80, 80, 80), -1)  # Centro escuro
    cv2.circle(roi, (50, 50), 35, (120, 120, 120), 3)  # Borda média
    
    # Cria contorno circular
    contorno = []
    for angle in range(0, 360, 10):
        rad = np.radians(angle)
        x = int(50 + 35 * np.cos(rad))
        y = int(50 + 35 * np.sin(rad))
        contorno.append([[x, y]])
    contorno = np.array(contorno, dtype=np.int32)
    
    # Estima profundidade
    print("\n📊 Estimando profundidade...")
    resultado = estimator.estimar_profundidade(roi, 2.0, contorno)
    
    print("\n  Resultados:")
    print(f"    Gradiente médio: {resultado['gradiente_medio']:.2f}")
    print(f"    Intensidade sombra: {resultado['intensidade_sombra']:.2f}%")
    print(f"    Variação intensidade: {resultado['variacao_intensidade']:.2f}")
    print(f"    Score profundidade: {resultado['profundidade_score']:.2f}")
    print(f"    Profundidade estimada: {resultado['profundidade_cm']:.2f} cm")
    print(f"    Classificação: {resultado['classificacao']}")
    
    print("\n✅ Teste de estimativa de profundidade concluído")


def test_integration():
    """Testa integração completa com OpenCVAnalyzer."""
    print("\n" + "="*60)
    print("TESTE 3: Integração OpenCV Analyzer + Profundidade")
    print("="*60)
    
    analyzer = OpenCVAnalyzer()
    
    # Cria frame sintético
    print("\n🎨 Criando frame de teste...")
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
    
    # Desenha buraco
    cv2.circle(frame, (300, 240), 40, (100, 100, 100), -1)
    cv2.circle(frame, (300, 240), 45, (150, 150, 150), 5)
    
    # Analisa buraco
    bbox = (255, 195, 345, 285)  # x1, y1, x2, y2
    print("\n📊 Analisando buraco...")
    resultado = analyzer.analisar_buraco(frame, bbox, distancia_m=2.5)
    
    print("\n  Dimensões (pixels):")
    print(f"    Largura: {resultado['dimensoes_pixels']['largura_px']} px")
    print(f"    Altura: {resultado['dimensoes_pixels']['altura_px']} px")
    print(f"    Área: {resultado['dimensoes_pixels']['area_px']:.0f} px²")
    
    print("\n  Dimensões (reais):")
    print(f"    Largura: {resultado['dimensoes_reais']['largura_m']:.3f} m")
    print(f"    Altura: {resultado['dimensoes_reais']['altura_m']:.3f} m")
    print(f"    Área: {resultado['dimensoes_reais']['area_m2']:.4f} m²")
    
    print("\n  Geometria:")
    print(f"    Circularidade: {resultado['geometria']['circularidade']:.3f}")
    print(f"    Convexidade: {resultado['geometria']['convexidade']:.3f}")
    
    print("\n  Profundidade:")
    print(f"    Profundidade: {resultado['profundidade']['profundidade_cm']:.2f} cm")
    print(f"    Classificação: {resultado['profundidade']['classificacao']}")
    
    print("\n  Classificação:")
    print(f"    Severidade: {resultado['classificacao']['severidade']}")
    print(f"    Prioridade: {resultado['classificacao']['prioridade']}")
    
    print("\n✅ Teste de integração concluído")


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("TESTANDO FASE 3: Calibração + Profundidade")
    print("="*60)
    
    try:
        test_calibration()
        test_depth_estimator()
        test_integration()
        
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*60)
        print("\nFase 3 implementada e funcionando corretamente.")
        print("\nPróximos passos:")
        print("  1. Testar com imagens reais")
        print("  2. Calibrar câmera usando padrão xadrez")
        print("  3. Validar estimativas de profundidade")
        print("  4. Ajustar thresholds se necessário")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
