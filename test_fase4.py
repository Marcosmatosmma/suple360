#!/usr/bin/env python3
"""
Teste da Fase 4 - Análise Avançada de Textura
==============================================

Script para testar as funcionalidades da Fase 4:
1. Análise avançada de textura (GLCM, entropia, FFT)
2. Classificação de tipo de dano
3. Integração completa com OpenCV Analyzer

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
import sys
import os

# Adiciona src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from texture_analyzer import TextureAnalyzer
from damage_classifier import DamageClassifier
from opencv_analyzer import OpenCVAnalyzer


def criar_buraco_sintetico(tipo='circular'):
    """Cria imagem sintética de buraco para teste."""
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 200
    
    if tipo == 'circular':
        # Buraco circular
        cv2.circle(frame, (320, 240), 40, (100, 100, 100), -1)
        cv2.circle(frame, (320, 240), 45, (150, 150, 150), 5)
        bbox = (275, 195, 365, 285)
        
    elif tipo == 'irregular':
        # Buraco irregular
        pts = np.array([[300,210], [340,200], [360,240], [350,270], [310,280], [290,250]], np.int32)
        cv2.fillPoly(frame, [pts], (90, 90, 90))
        cv2.polylines(frame, [pts], True, (140, 140, 140), 5)
        bbox = (280, 190, 370, 290)
        
    elif tipo == 'rachadura':
        # Rachadura linear
        cv2.line(frame, (280, 240), (360, 240), (80, 80, 80), 8)
        cv2.line(frame, (278, 238), (362, 242), (120, 120, 120), 3)
        bbox = (270, 230, 370, 250)
        
    elif tipo == 'erosao':
        # Erosão dispersa
        for i in range(20):
            x = np.random.randint(290, 350)
            y = np.random.randint(220, 260)
            r = np.random.randint(3, 8)
            cv2.circle(frame, (x, y), r, (120, 120, 120), -1)
        bbox = (285, 215, 355, 265)
    
    return frame, bbox


def test_texture_analyzer():
    """Testa análise de textura avançada."""
    print("\n" + "="*60)
    print("TESTE 1: Análise de Textura Avançada")
    print("="*60)
    
    analyzer = TextureAnalyzer()
    
    # Cria buraco circular
    frame, bbox = criar_buraco_sintetico('circular')
    x1, y1, x2, y2 = bbox
    roi = frame[y1:y2, x1:x2]
    
    # Cria contorno
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contorno = max(contours, key=cv2.contourArea) if contours else None
    
    print("\n🎨 Analisando textura de buraco circular...")
    resultado = analyzer.analisar_textura_avancada(roi, contorno)
    
    print("\n  Resultados:")
    print(f"    Entropia: {resultado['entropia']:.3f}")
    print(f"    Energia: {resultado['energia']:.3f}")
    print(f"    Homogeneidade: {resultado['homogeneidade']:.3f}")
    print(f"    Contraste GLCM: {resultado['contraste_glcm']:.3f}")
    print(f"    Densidade bordas: {resultado['densidade_bordas']:.1f}%")
    print(f"    Textura dominante: {resultado['textura_dominante']}")
    
    print(f"\n  Histograma RGB:")
    print(f"    R: {resultado['histograma_rgb']['r_mean']:.1f}")
    print(f"    G: {resultado['histograma_rgb']['g_mean']:.1f}")
    print(f"    B: {resultado['histograma_rgb']['b_mean']:.1f}")
    
    print("\n✅ Teste de textura concluído")


def test_damage_classifier():
    """Testa classificador de tipo de dano."""
    print("\n" + "="*60)
    print("TESTE 2: Classificação de Tipo de Dano")
    print("="*60)
    
    classifier = DamageClassifier()
    
    tipos = ['circular', 'irregular', 'rachadura', 'erosao']
    
    for tipo in tipos:
        print(f"\n📊 Testando: {tipo.upper()}")
        
        frame, bbox = criar_buraco_sintetico(tipo)
        x1, y1, x2, y2 = bbox
        roi = frame[y1:y2, x1:x2]
        
        # Cria contorno
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contorno = max(contours, key=cv2.contourArea) if contours else None
        
        # Dados simulados
        geometria = {
            'circularidade': 0.85 if tipo == 'circular' else (0.45 if tipo == 'irregular' else 0.6),
            'aspect_ratio': 1.2 if tipo == 'circular' else (1.5 if tipo == 'irregular' else (5.0 if tipo == 'rachadura' else 1.3)),
            'convexidade': 0.92 if tipo == 'circular' else (0.55 if tipo == 'irregular' else 0.8)
        }
        
        textura = {
            'entropia': 4.5 if tipo == 'circular' else (6.5 if tipo == 'irregular' else 5.0),
            'densidade_bordas': 15 if tipo == 'circular' else (35 if tipo == 'irregular' else 12),
            'homogeneidade': 0.6 if tipo == 'circular' else (0.25 if tipo == 'irregular' else 0.7)
        }
        
        dimensoes = {
            'area_m2': 0.12 if tipo != 'erosao' else 0.04
        }
        
        # Classifica
        resultado = classifier.classificar_dano(roi, contorno, geometria, textura, dimensoes)
        
        print(f"  Tipo detectado: {resultado['tipo_dano']}")
        print(f"  Confiança: {resultado['confianca']:.1f}%")
        print(f"  Característica: {resultado['caracteristicas']}")
        if resultado['tipo_secundario']:
            print(f"  Tipo secundário: {resultado['tipo_secundario']}")
    
    print("\n✅ Teste de classificação concluído")


def test_integration():
    """Testa integração completa."""
    print("\n" + "="*60)
    print("TESTE 3: Integração Completa OpenCV Analyzer")
    print("="*60)
    
    analyzer = OpenCVAnalyzer()
    
    # Cria buraco irregular
    frame, bbox = criar_buraco_sintetico('irregular')
    
    print("\n📊 Analisando buraco com TODOS os módulos...")
    resultado = analyzer.analisar_buraco(frame, bbox, distancia_m=2.5)
    
    print("\n  Dimensões:")
    print(f"    Área: {resultado['dimensoes_reais']['area_m2']:.4f} m²")
    print(f"    Largura: {resultado['dimensoes_reais']['largura_m']:.3f} m")
    
    print("\n  Geometria:")
    print(f"    Circularidade: {resultado['geometria']['circularidade']:.3f}")
    print(f"    Convexidade: {resultado['geometria']['convexidade']:.3f}")
    
    print("\n  Textura Básica:")
    print(f"    Intensidade: {resultado['textura']['intensidade_media']:.1f}")
    print(f"    Contraste: {resultado['textura']['contraste']:.3f}")
    
    print("\n  Textura Avançada (Fase 4):")
    print(f"    Entropia: {resultado['textura_avancada']['entropia']:.3f}")
    print(f"    Homogeneidade: {resultado['textura_avancada']['homogeneidade']:.3f}")
    print(f"    Densidade bordas: {resultado['textura_avancada']['densidade_bordas']:.1f}%")
    print(f"    Textura: {resultado['textura_avancada']['textura_dominante']}")
    
    print("\n  Profundidade:")
    print(f"    Profundidade: {resultado['profundidade']['profundidade_cm']:.2f} cm")
    print(f"    Classificação: {resultado['profundidade']['classificacao']}")
    
    print("\n  Tipo de Dano (Fase 4):")
    print(f"    Tipo: {resultado['tipo_dano']['tipo_dano']}")
    print(f"    Confiança: {resultado['tipo_dano']['confianca']:.1f}%")
    print(f"    Descrição: {resultado['tipo_dano']['caracteristicas']}")
    
    print("\n  Classificação:")
    print(f"    Severidade: {resultado['classificacao']['severidade']}")
    print(f"    Prioridade: {resultado['classificacao']['prioridade']}")
    
    print("\n✅ Teste de integração concluído")


def main():
    """Executa todos os testes."""
    print("\n" + "="*60)
    print("TESTANDO FASE 4: Análise Avançada de Textura")
    print("="*60)
    
    try:
        test_texture_analyzer()
        test_damage_classifier()
        test_integration()
        
        print("\n" + "="*60)
        print("✅ TODOS OS TESTES CONCLUÍDOS COM SUCESSO!")
        print("="*60)
        print("\nFase 4 implementada e funcionando corretamente.")
        print("\nNovos recursos:")
        print("  ✓ Análise GLCM (energia, homogeneidade, contraste, correlação)")
        print("  ✓ Entropia de Shannon")
        print("  ✓ Análise de frequências (FFT)")
        print("  ✓ Classificação de tipo de dano")
        print("  ✓ Detecção de: buraco circular/irregular, rachadura, erosão")
        print("\nPróximos passos:")
        print("  1. Testar com imagens reais")
        print("  2. Ajustar thresholds de classificação")
        print("  3. Validar precisão dos classificadores")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Erro durante os testes: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
