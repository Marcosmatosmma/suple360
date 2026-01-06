"""
Gerador de Padrões de Calibração
=================================

Gera padrões de calibração (xadrez e ArUco) para impressão e exportação em PDF.

Autor: Sistema de Detecção de Buracos
Data: 2026-01-06
"""

import cv2
import numpy as np
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO
import os


class CalibrationPatternGenerator:
    """
    Gera padrões de calibração para impressão.
    """
    
    def __init__(self):
        """Inicializa o gerador."""
        self.a4_width, self.a4_height = A4  # 595 x 842 pontos
    
    def gerar_padrao_xadrez(
        self, 
        pattern_size=(9, 6),
        square_size_mm=25,
        output_path='padrao_xadrez.pdf'
    ):
        """
        Gera padrão xadrez para calibração e salva em PDF.
        
        Args:
            pattern_size: Tupla (cols, rows) de cantos internos
            square_size_mm: Tamanho do quadrado em milímetros
            output_path: Caminho do arquivo PDF de saída
            
        Returns:
            str: Caminho do arquivo gerado
        """
        cols, rows = pattern_size
        
        # Cria imagem do xadrez (adiciona 1 para ter bordas)
        board_cols = cols + 1
        board_rows = rows + 1
        
        # Tamanho em pixels (alta resolução para impressão: 300 DPI)
        dpi = 300
        mm_to_inch = 0.0393701
        pixels_per_mm = dpi * mm_to_inch
        
        square_size_px = int(square_size_mm * pixels_per_mm)
        img_width = board_cols * square_size_px
        img_height = board_rows * square_size_px
        
        # Cria imagem
        img = np.zeros((img_height, img_width), dtype=np.uint8)
        
        # Desenha quadrados
        for i in range(board_rows):
            for j in range(board_cols):
                if (i + j) % 2 == 0:
                    y1 = i * square_size_px
                    y2 = (i + 1) * square_size_px
                    x1 = j * square_size_px
                    x2 = (j + 1) * square_size_px
                    img[y1:y2, x1:x2] = 255
        
        # Converte para PDF
        self._criar_pdf_xadrez(
            img, 
            pattern_size, 
            square_size_mm,
            output_path
        )
        
        return output_path
    
    def gerar_aruco_markers(
        self,
        num_markers=10,
        marker_size_mm=50,
        dictionary_type=cv2.aruco.DICT_6X6_250,
        output_path='aruco_markers.pdf'
    ):
        """
        Gera múltiplos markers ArUco e salva em PDF.
        
        Args:
            num_markers: Número de markers a gerar (1-20)
            marker_size_mm: Tamanho do marker em milímetros
            dictionary_type: Tipo de dicionário ArUco
            output_path: Caminho do arquivo PDF de saída
            
        Returns:
            str: Caminho do arquivo gerado
        """
        # Cria dicionário ArUco
        dictionary = cv2.aruco.getPredefinedDictionary(dictionary_type)
        
        # Gera markers
        markers = []
        for marker_id in range(min(num_markers, 20)):
            # Cria marker de 200x200 pixels (alta resolução)
            marker_img = cv2.aruco.generateImageMarker(
                dictionary, 
                marker_id, 
                200,
                borderBits=1
            )
            markers.append((marker_id, marker_img))
        
        # Cria PDF
        self._criar_pdf_aruco(markers, marker_size_mm, output_path)
        
        return output_path
    
    def _criar_pdf_xadrez(
        self, 
        img, 
        pattern_size, 
        square_size_mm,
        output_path
    ):
        """
        Cria PDF com padrão xadrez.
        
        Args:
            img: Imagem do xadrez (numpy array)
            pattern_size: Tupla (cols, rows)
            square_size_mm: Tamanho do quadrado em mm
            output_path: Caminho de saída
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, self.a4_height - 50, 
                     "Padrão de Calibração - Xadrez")
        
        # Instruções
        c.setFont("Helvetica", 10)
        y_pos = self.a4_height - 80
        
        instrucoes = [
            f"Tamanho do padrão: {pattern_size[0]}x{pattern_size[1]} cantos internos",
            f"Tamanho do quadrado: {square_size_mm}mm",
            "",
            "INSTRUÇÕES:",
            "1. Imprima esta página em A4 (sem escalar)",
            "2. Cole em superfície plana e rígida",
            "3. Tire 15-20 fotos do padrão em diferentes ângulos",
            "4. Certifique-se que todo o padrão está visível",
            "5. Use boa iluminação",
            "6. Execute: python3 calibrate_camera.py --images fotos/*.jpg"
        ]
        
        for linha in instrucoes:
            c.drawString(50, y_pos, linha)
            y_pos -= 15
        
        # Converte imagem OpenCV para PIL/ReportLab
        img_pil = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        
        # Salva temporariamente em BytesIO
        buffer = BytesIO()
        from PIL import Image
        Image.fromarray(img_pil).save(buffer, format='PNG')
        buffer.seek(0)
        
        # Calcula tamanho para caber na página
        # Deixa margens de 50 pontos
        max_width = self.a4_width - 100
        max_height = 400
        
        # Escala mantendo proporção
        img_ratio = img.shape[1] / img.shape[0]
        if max_width / img_ratio <= max_height:
            img_w = max_width
            img_h = max_width / img_ratio
        else:
            img_h = max_height
            img_w = max_height * img_ratio
        
        # Centraliza horizontalmente
        x_pos = (self.a4_width - img_w) / 2
        y_pos = 100
        
        # Adiciona imagem
        c.drawImage(ImageReader(buffer), x_pos, y_pos, 
                    width=img_w, height=img_h)
        
        # Rodapé
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, 
                     f"Gerado por: Sistema de Detecção de Buracos - {output_path}")
        
        c.save()
    
    def _criar_pdf_aruco(self, markers, marker_size_mm, output_path):
        """
        Cria PDF com markers ArUco em uma única página.
        
        Args:
            markers: Lista de tuplas (id, img)
            marker_size_mm: Tamanho do marker em mm
            output_path: Caminho de saída
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # Título
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, self.a4_height - 40, "Markers ArUco - Calibração")
        
        # Instruções curtas
        c.setFont("Helvetica", 8)
        y_pos = self.a4_height - 60
        c.drawString(50, y_pos, f"1. Imprima em A4 (100% de escala)  2. Recorte cada marker  3. Meça: {marker_size_mm}mm × {marker_size_mm}mm  4. Cole em superfície plana")
        
        # Grid de markers: 2 colunas × 5 linhas = 10 markers
        markers_per_row = 2
        markers_per_col = 5
        
        # Tamanho do marker em pontos (1mm = 2.83465 pontos)
        mm_to_points = 2.83465
        marker_size_pts = marker_size_mm * mm_to_points
        
        # Área disponível
        start_y = self.a4_height - 100
        usable_height = start_y - 80  # Deixa espaço para rodapé
        usable_width = self.a4_width - 100
        
        # Espaçamento entre markers
        spacing_x = (usable_width - (markers_per_row * marker_size_pts)) / (markers_per_row + 1)
        spacing_y = (usable_height - (markers_per_col * marker_size_pts)) / (markers_per_col + 1)
        
        # Label ocupa espaço abaixo do marker
        label_space = 25
        
        for idx, (marker_id, marker_img) in enumerate(markers):
            row = idx // markers_per_row
            col = idx % markers_per_row
            
            # Posição do marker
            x = 50 + spacing_x + col * (marker_size_pts + spacing_x)
            y = start_y - spacing_y - marker_size_pts - row * (marker_size_pts + spacing_y + label_space)
            
            # Converte marker para PIL
            marker_pil = cv2.cvtColor(marker_img, cv2.COLOR_GRAY2RGB)
            buffer = BytesIO()
            from PIL import Image
            Image.fromarray(marker_pil).save(buffer, format='PNG')
            buffer.seek(0)
            
            # Desenha marker
            c.drawImage(ImageReader(buffer), x, y, 
                       width=marker_size_pts, height=marker_size_pts)
            
            # Label do marker (centralizado)
            c.setFont("Helvetica-Bold", 9)
            label_text = f"ID:{marker_id}"
            text_width = c.stringWidth(label_text, "Helvetica-Bold", 9)
            c.drawString(x + (marker_size_pts - text_width) / 2, y - 15, label_text)
            
            c.setFont("Helvetica", 7)
            size_text = f"{marker_size_mm}mm"
            text_width = c.stringWidth(size_text, "Helvetica", 7)
            c.drawString(x + (marker_size_pts - text_width) / 2, y - 23, size_text)
        
        # Rodapé
        c.setFont("Helvetica", 7)
        c.drawString(50, 30, f"DICT_6X6_250 | Gerado: Sistema Suple360 v2")
        c.drawString(450, 30, "Página única")
        
        c.save()
    
    def gerar_pagina_calibracao_completa(
        self,
        output_dir='calibracao_pdfs'
    ):
        """
        Gera PDFs completos de calibração (xadrez + ArUco).
        
        Args:
            output_dir: Diretório de saída
            
        Returns:
            dict: Caminhos dos arquivos gerados
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Gera padrão xadrez
        xadrez_path = os.path.join(output_dir, 'padrao_xadrez.pdf')
        self.gerar_padrao_xadrez(
            pattern_size=(9, 6),
            square_size_mm=25,
            output_path=xadrez_path
        )
        
        # Gera markers ArUco
        aruco_path = os.path.join(output_dir, 'aruco_markers.pdf')
        self.gerar_aruco_markers(
            num_markers=10,
            marker_size_mm=100,
            output_path=aruco_path
        )
        
        return {
            'xadrez': xadrez_path,
            'aruco': aruco_path
        }


# Teste standalone
if __name__ == '__main__':
    print("🎨 Gerador de Padrões de Calibração\n")
    
    generator = CalibrationPatternGenerator()
    
    print("Gerando padrões de calibração...")
    arquivos = generator.gerar_pagina_calibracao_completa()
    
    print(f"\n✅ Arquivos gerados:")
    print(f"   📄 Xadrez: {arquivos['xadrez']}")
    print(f"   📄 ArUco: {arquivos['aruco']}")
    print(f"\n💡 Imprima estes PDFs em A4 sem escalar!")
