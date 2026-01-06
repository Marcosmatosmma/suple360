#!/usr/bin/env python3
"""
Script de Calibração de Câmera
===============================

Script para calibrar a câmera do sistema usando padrão xadrez.
Salva os parâmetros de calibração para uso posterior.

Uso:
    1. Imprima um padrão xadrez 9x6 (64 quadrados)
    2. Tire 15-20 fotos do padrão em diferentes ângulos
    3. Execute: python3 calibrate_camera.py --images calibracao/*.jpg

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import argparse
import os
import glob
from src.calibration import CameraCalibrator


def main():
    """Função principal do script de calibração."""
    parser = argparse.ArgumentParser(
        description='Calibra a câmera usando padrão xadrez'
    )
    parser.add_argument(
        '--images',
        type=str,
        required=True,
        help='Caminho para as imagens de calibração (ex: calibracao/*.jpg)'
    )
    parser.add_argument(
        '--pattern-width',
        type=int,
        default=9,
        help='Número de cantos internos na largura do xadrez (padrão: 9)'
    )
    parser.add_argument(
        '--pattern-height',
        type=int,
        default=6,
        help='Número de cantos internos na altura do xadrez (padrão: 6)'
    )
    parser.add_argument(
        '--square-size',
        type=float,
        default=0.025,
        help='Tamanho do quadrado em metros (padrão: 0.025 = 2.5cm)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='camera_calibration.pkl',
        help='Arquivo de saída para calibração (padrão: camera_calibration.pkl)'
    )
    
    args = parser.parse_args()
    
    # Expande glob pattern
    image_paths = glob.glob(args.images)
    
    if len(image_paths) == 0:
        print(f"❌ Erro: Nenhuma imagem encontrada em '{args.images}'")
        print("\nDica: Use um padrão como 'calibracao/*.jpg' ou 'calibracao/*.png'")
        return 1
    
    print(f"\n📸 Encontradas {len(image_paths)} imagens para calibração")
    print(f"🎯 Padrão xadrez: {args.pattern_width}x{args.pattern_height} cantos")
    print(f"📏 Tamanho do quadrado: {args.square_size}m\n")
    
    # Cria calibrador
    calibrator = CameraCalibrator(
        pattern_size=(args.pattern_width, args.pattern_height),
        square_size=args.square_size
    )
    
    # Calibra
    print("🔄 Iniciando calibração...")
    success = calibrator.calibrate_from_images(image_paths)
    
    if not success:
        print("\n❌ Calibração falhou!")
        print("Dicas:")
        print("  - Tire mais fotos (15-20 recomendado)")
        print("  - Varie os ângulos e posições do padrão")
        print("  - Certifique-se que o padrão está completamente visível")
        print("  - Use boa iluminação")
        return 1
    
    # Salva calibração
    print(f"\n💾 Salvando calibração em '{args.output}'...")
    calibrator.save_calibration(args.output)
    
    print("\n✅ Calibração concluída com sucesso!")
    print(f"\nPara usar a calibração, carregue o arquivo '{args.output}'")
    print("no seu código:")
    print(f"  calibrator.load_calibration('{args.output}')")
    
    return 0


if __name__ == '__main__':
    exit(main())
