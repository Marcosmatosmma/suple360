# 📚 Tutorial: Sistema de Detecção de Buracos

## 📖 Índice
1. [Visão Geral](#visão-geral)
2. [Estrutura do Projeto](#estrutura-do-projeto)
3. [Módulos Detalhados](#módulos-detalhados)
4. [Fluxo de Execução](#fluxo-de-execução)
5. [Variáveis Importantes](#variáveis-importantes)

---

## 🎯 Visão Geral

Este sistema detecta buracos em tempo real usando:
- **Câmera Raspberry Pi** para captura de imagens
- **YOLO (Ultralytics)** para detecção de objetos
- **LIDAR** para medir distâncias
- **Flask** para interface web
- **SQLite** para armazenar detecções

### Como funciona?
1. A câmera captura frames continuamente
2. O YOLO analisa cada frame em busca de buracos
3. O LIDAR fornece a distância dos objetos detectados
4. Os dados são salvos no banco SQLite
5. A interface web mostra tudo em tempo real

---

## 📁 Estrutura do Projeto

```
src/
├── main.py            # 🚀 Arquivo principal - inicia tudo
├── database.py        # 💾 Gerencia o banco de dados SQLite
├── camera.py          # 📷 Captura frames da câmera
├── detector.py        # 🔍 Detecta buracos com YOLO
├── lidar_manager.py   # 📡 Lê dados do sensor LIDAR
├── api.py             # 🌐 Rotas da API Flask
├── utils.py           # 🛠️ Funções auxiliares
├── opencv_analyzer.py # 🎨 Análise geométrica com OpenCV (FASE 1)
├── tracker.py         # 🎯 Rastreamento de buracos (FASE 1)
├── mapper.py          # 🗺️ Construtor de mapas 2D (FASE 2)
├── map_utils.py       # 🧭 Conversões de coordenadas (FASE 2)
├── calibration.py       # 📐 Calibração de câmera (FASE 3)
├── depth_estimator.py   # 🔬 Estimativa de profundidade (FASE 3)
├── texture_analyzer.py  # 🎨 Análise avançada de textura (FASE 4)
├── damage_classifier.py # 🔍 Classificação de tipo de dano (FASE 4)
├── roi_detector.py      # ⚡ Detecção de ROI (FASE 5)
├── motion_detector.py   # ⚡ Detecção de movimento (FASE 5)
└── performance_optimizer.py # ⚡ Multi-threading e otimização (FASE 5)
```

---

## 📦 Módulos Detalhados

### 1. `main.py` - Arquivo Principal

**O que faz:** Inicializa e coordena todos os componentes do sistema.

```python
def main():
    """Função principal de inicialização"""
```

#### Passo a Passo:

**1. Cria diretório para salvar fotos**
```python
screenshot_dir = '/home/suple/Desktop/suple360v2/deteccoes'
os.makedirs(screenshot_dir, exist_ok=True)
```
- `screenshot_dir`: caminho onde as fotos serão salvas
- `exist_ok=True`: não dá erro se a pasta já existir

**2. Inicializa o Banco de Dados**
```python
db_manager = DatabaseManager()
```
- `db_manager`: objeto que gerencia todas as operações do banco
- Cria as tabelas automaticamente se não existirem

**3. Inicializa o LIDAR**
```python
lidar_manager = LidarManager(
    port="/dev/ttyUSB0",     # Porta USB onde o LIDAR está conectado
    baud=115200,             # Velocidade de comunicação (bits por segundo)
    sector_deg=5             # Agrupa leituras a cada 5 graus
)
lidar_manager.start()
```

**4. Carrega o Modelo YOLO**
```python
model = YOLO('/home/suple/Desktop/suple360v2/model/best.pt')
```
- `best.pt`: arquivo do modelo treinado para detectar buracos

**5. Inicializa a Câmera**
```python
camera = picamera2.Picamera2()
config = camera.create_preview_configuration(main={"size": (1280, 720)})
```
- Resolução: 1280x720 pixels (HD)
- Balanceia qualidade e velocidade de processamento

**6. Inicia Gerenciador da Câmera**
```python
camera_manager = CameraManager(camera)
camera_manager.start()
```
- Captura frames em uma thread separada
- Mantém o stream fluido

**7. Inicia o Detector**
```python
detector = Detector(
    model=model,                    # Modelo YOLO
    db_manager=db_manager,          # Banco de dados
    lidar_manager=lidar_manager,    # Sensor LIDAR
    camera_manager=camera_manager,  # Câmera
    screenshot_dir=screenshot_dir,  # Onde salvar fotos
    cam_hfov_deg=70.0              # Campo de visão horizontal (70°)
)
detector.start()
```

**8. Inicia Servidor Web**
```python
app = create_app(db_manager, camera_manager, lidar_manager)
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()
```
- `daemon=True`: a thread fecha quando o programa principal fechar
- Roda na porta 5000

---

### 2. `database.py` - Gerenciamento de Dados

**O que faz:** Armazena e recupera detecções do banco SQLite.

#### Classe `DatabaseManager`

**Variáveis de Instância:**
```python
self.db_path = "deteccoes/detections.db"  # Caminho do arquivo do banco
self.lock = threading.Lock()               # Previne conflitos entre threads
```

#### Tabelas do Banco:

**1. Tabela `detections`** (Detecções principais)
```sql
id              # Identificador único (auto-incremento)
timestamp       # Data/hora da detecção ("2026-01-05 20:08:33")
photo_path      # Nome do arquivo da foto ("buraco_20260105_200833_1.jpg")
num_buracos     # Quantidade de buracos detectados
created_at      # Quando o registro foi criado
```

**2. Tabela `buracos`** (Detalhes de cada buraco)
```sql
id              # Identificador único
detection_id    # Liga ao registro da tabela detections
bbox_x1, y1     # Canto superior esquerdo do retângulo
bbox_x2, y2     # Canto inferior direito do retângulo
confianca       # Confiança da detecção (0.0 a 1.0)
distancia_m     # Distância em metros (do LIDAR)
largura_m       # Largura estimada em metros
```

#### Métodos Principais:

**`add_detection(photo_path, boxes, timestamp)`**
- Salva uma nova detecção no banco
- `photo_path`: nome da foto (ex: "buraco_20260105_200833_1.jpg")
- `boxes`: lista de buracos detectados
- `timestamp`: momento da detecção

**`get_recent(limit=20)`**
- Retorna as últimas detecções
- `limit`: quantas detecções retornar (padrão: 20)

**`get_stats()`**
- Retorna estatísticas gerais:
  - Total de detecções
  - Total de buracos

---

### 3. `camera.py` - Captura de Imagens

**O que faz:** Captura frames da câmera continuamente e aplica overlays visuais.

#### Classe `CameraManager`

**Variáveis de Instância:**
```python
self.camera           # Objeto da câmera Picamera2
self.frame_global     # Frame com desenhos (enviado para a web)
self.latest_frame     # Frame original mais recente
self.detection_boxes  # Lista de caixas delimitadoras atuais
self.detection_text   # Texto de status ("Buraco detectado!")
self.detection_color  # Cor do texto (verde ou vermelho)
self.lock            # Previne conflitos entre threads
self.frame_count     # Contador de frames capturados
```

#### Métodos Principais:

**`get_latest_frame()`**
- Retorna uma cópia do último frame capturado
- Usado pelo detector para análise

**`update_detections(boxes, text, color)`**
- Atualiza as informações de detecção para desenhar
- `boxes`: lista com coordenadas dos buracos
- `text`: mensagem de status
- `color`: cor (verde = OK, vermelho = buraco detectado)

**`capture_loop()`** - Loop principal de captura
```python
while True:
    frame = self.camera.capture_array()  # Captura frame
    
    # Converte formato de cor
    if frame.shape[2] == 4:
        frame = frame[:, :, :3]          # Remove canal alpha
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    self.frame_count += 1                # Incrementa contador
    
    # Desenha overlays (boxes, texto)
    frame_vis = draw_overlays(frame.copy(), boxes, text, color, frame_id)
    
    self.frame_global = frame_vis        # Atualiza frame para stream
```

---

### 4. `detector.py` - Detecção de Buracos

**O que faz:** Usa YOLO para detectar buracos e funde com dados do LIDAR.

#### Classe `Detector`

**Variáveis de Instância:**
```python
self.model              # Modelo YOLO treinado
self.db_manager         # Gerenciador do banco de dados
self.lidar_manager      # Gerenciador do LIDAR
self.camera_manager     # Gerenciador da câmera
self.screenshot_dir     # Pasta para salvar fotos
self.cam_hfov_deg       # Campo de visão horizontal (70°)
self.detection_counter  # Contador de detecções
```

#### Método Principal: `detection_loop()`

**Passo 1: Redimensiona frame para detecção**
```python
target_w, target_h = 640, 360
det_input = cv2.resize(frame, (target_w, target_h))
results = self.model(det_input)
```
- Reduz resolução para processar mais rápido
- 640x360 é suficiente para detecção precisa

**Passo 2: Processa cada detecção**
```python
for result in results:
    for box in result.boxes:
        x1, y1, x2, y2 = box.xyxy[0]  # Coordenadas do retângulo
        conf = box.conf[0]             # Confiança (0.0 a 1.0)
```

**Passo 3: Calcula ângulo e distância**
```python
x_center = (x1 + x2) / 2.0           # Centro do buraco
rel = (x_center / frame_w) - 0.5     # Posição relativa (-0.5 a 0.5)
angle_deg = rel * self.cam_hfov_deg  # Converte para ângulo

dist_m = self.lidar_manager.sector_to_distance(angle_deg)
```
- Se o buraco está no centro: `angle_deg = 0°`
- Se está na esquerda: `angle_deg` negativo
- Se está na direita: `angle_deg` positivo

**Passo 4: Estima largura do buraco**
```python
if dist_m is not None:
    box_ang = ((x2 - x1) / frame_w) * self.cam_hfov_deg
    width_m = dist_m * 2 * 3.14159 * (box_ang / 360.0)
```
- Usa geometria: largura = distância × ângulo
- Quanto mais longe, maior a largura real

**Passo 5: Salva detecção**
```python
if new_boxes:
    filename = f"buraco_{time.strftime('%Y%m%d_%H%M%S')}_{counter}.jpg"
    cv2.imwrite(full_path, annotated)
    
    self.db_manager.add_detection(
        photo_path=filename,
        boxes=new_boxes,
        timestamp=timestamp
    )
```

---

### 5. `lidar_manager.py` - Sensor de Distância

**O que faz:** Lê dados do sensor LIDAR e os organiza por setores angulares.

#### Classe `LidarManager`

**Variáveis de Instância:**
```python
self.port = "/dev/ttyUSB0"    # Porta USB do LIDAR
self.baud = 115200            # Taxa de comunicação
self.sector_deg = 5           # Tamanho de cada setor (5°)
self.data = {}                # Dicionário: {ângulo: distância}
self.lock = threading.Lock()  # Sincronização entre threads
```

#### Como funciona o LIDAR?

**1. Leitura em 360 graus**
```
  0° (frente)
   |
   |
270°--+--90°
   |
   |
  180° (trás)
```

**2. Agregação por setores**
```python
sector = int(round(angle / self.sector_deg) * self.sector_deg) % 360
```
- Ângulos 0-4° → Setor 0°
- Ângulos 5-9° → Setor 5°
- Ângulos 10-14° → Setor 10°
- E assim por diante...

**3. Guarda menor distância**
```python
agg[sector] = min(agg.get(sector, distance), distance)
```
- Se houver múltiplas leituras no mesmo setor, guarda a menor
- Isso detecta o objeto mais próximo

#### Método `sector_to_distance(angle_deg)`
```python
def sector_to_distance(self, angle_deg):
    angle_norm = angle_deg % 360              # Normaliza: -10° vira 350°
    sector = int(round(angle_norm / 5) * 5)   # Arredonda para setor
    return self.data.get(sector)              # Retorna distância
```

**Exemplo:**
- Buraco detectado a `angle_deg = 12°`
- Setor mais próximo: `10°`
- Retorna a distância armazenada para o setor 10°

---

### 6. `api.py` - Interface Web

**O que faz:** Cria rotas HTTP para acessar o sistema via navegador.

#### Principais Rotas:

**`/` - Página inicial**
```python
@app.route('/')
def index():
    return render_template('index.html')
```

**`/video_feed` - Stream de vídeo**
```python
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                   mimetype='multipart/x-mixed-replace; boundary=frame')
```
- Envia frames continuamente (MJPEG)
- Atualiza a imagem no navegador em tempo real

**`/api/detections/recent` - Últimas detecções**
```python
@app.route('/api/detections/recent')
def get_recent_detections():
    detections = db_manager.get_recent(limit=20)
    return jsonify({"detections": detections})
```
- Retorna JSON com as últimas 20 detecções

**`/api/lidar/latest` - Dados do LIDAR**
```python
@app.route('/api/lidar/latest')
def lidar_latest():
    data = lidar_manager.get_data()
    return jsonify({
        "sectors": data,
        "sector_deg": 5,
        "available": True
    })
```

**`/deteccoes/<filename>` - Servir imagens**
```python
@app.route('/deteccoes/<path:filename>')
def serve_detection_image(filename):
    filepath = os.path.join(deteccoes_dir, filename)
    return send_file(filepath, mimetype='image/jpeg')
```

---

### 7. `utils.py` - Funções Auxiliares

**O que faz:** Funções para desenhar overlays nos frames.

#### Função `draw_overlays(frame, boxes, text, color, frame_id)`

**Parâmetros:**
- `frame`: imagem onde desenhar
- `boxes`: lista de retângulos [(x1,y1,x2,y2,conf,dist,width), ...]
- `text`: texto de status
- `color`: cor do texto (tupla RGB)
- `frame_id`: número do frame (opcional)

**O que desenha:**

**1. Número do frame**
```python
cv2.putText(frame, f"Frame {frame_id}", (10, 30), ...)
```
- Posição: canto superior esquerdo (10, 30)

**2. Retângulos ao redor de buracos**
```python
cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
```
- Cor verde: (0, 255, 0)
- Espessura: 2 pixels

**3. Labels com informações**
```python
label = f"Buraco {conf:.2f} | {dist_m:.1f}m | L~{width_m:.2f}m"
cv2.putText(frame, label, (x1, y1 - 10), ...)
```
- Exemplo: "Buraco 0.95 | 2.3m | L~0.45m"
- Posição: acima do retângulo

**4. Texto de status**
```python
cv2.putText(frame, text, (10, 70), ...)
```
- Exemplo: "✓ BURACO DETECTADO! (2 objeto(s))"

---

### 8. `opencv_analyzer.py` - Análise Geométrica (FASE 1) 🆕

**O que faz:** Analisa profundamente cada buraco usando técnicas avançadas de OpenCV.

#### Classe `OpenCVAnalyzer`

**Método Principal: `analisar_buraco(frame, bbox, distancia_m)`**

**Entrada:**
- `frame`: Imagem completa da câmera
- `bbox`: Coordenadas do buraco `(x1, y1, x2, y2)`
- `distancia_m`: Distância do LIDAR (opcional)

**Saída:** Dicionário completo com:

**1. Dimensões em Pixels**
```python
{
    'largura_px': 203,      # Largura em pixels
    'altura_px': 89,        # Altura em pixels
    'area_px': 14250,       # Área total
    'perimetro_px': 584     # Perímetro
}
```

**2. Dimensões Reais (em metros)**
```python
{
    'largura_m': 0.452,     # Largura real
    'altura_m': 0.321,      # Altura real
    'area_m2': 0.1145,      # Área em m²
    'perimetro_m': 1.423    # Perímetro em metros
}
```

**3. Geometria**
```python
{
    'aspect_ratio': 1.18,         # Proporção largura/altura
    'circularidade': 0.82,        # 0=irregular, 1=círculo perfeito
    'convexidade': 0.91,          # 0=muito irregular, 1=convexo
    'orientacao_deg': 23.4,       # Ângulo de rotação
    'elipse_eixo_maior': 0.50,    # Eixo maior da elipse ajustada
    'elipse_eixo_menor': 0.35     # Eixo menor
}
```

**4. Textura**
```python
{
    'intensidade_media': 87.3,    # Brilho médio (0-255)
    'desvio_padrao': 24.1,        # Variação de brilho
    'contraste': 0.68             # Contraste (0-1)
}
```

**5. Classificação Automática**
```python
{
    'severidade': 'media',         # leve / media / grave
    'necessita_reparo': True,      # Precisa consertar?
    'prioridade': 'media'          # baixa / media / alta
}
```

#### Como Funciona Internamente?

**Passo 1: Extração de Contorno**
```python
def _extrair_contorno(gray_image):
    # Binarização adaptativa (se adapta à iluminação)
    thresh = cv2.adaptiveThreshold(...)
    
    # Encontra contornos (bordas do buraco)
    contours = cv2.findContours(thresh, ...)
    
    # Retorna o maior contorno
    return max(contours, key=cv2.contourArea)
```

**Passo 2: Análise Geométrica**
```python
def _analisar_geometria(contorno):
    # Área do contorno
    area = cv2.contourArea(contorno)
    
    # Perímetro do contorno
    perimetro = cv2.arcLength(contorno, True)
    
    # Circularidade: 4π × área / perímetro²
    # Círculo perfeito = 1.0
    circularidade = (4 * π * area) / (perimetro²)
    
    # Convex Hull (envoltória convexa)
    hull = cv2.convexHull(contorno)
    convexidade = area / area_hull
    
    # Elipse ajustada
    ellipse = cv2.fitEllipse(contorno)
    # Retorna orientação e eixos
```

**Passo 3: Conversão Pixel → Metro**
```python
def _converter_para_metros(geometria, distancia_m):
    # Calcula largura real do campo de visão
    largura_real_m = 2 × distancia × tan(FOV/2)
    
    # Fator de conversão
    metros_por_pixel = largura_real_m / largura_px
    
    # Converte todas as medidas
    area_m2 = area_px × (metros_por_pixel)²
```

**Passo 4: Classificação de Severidade**
```python
def _classificar_severidade(area_m2, circularidade):
    if area_m2 < 0.05 and circularidade > 0.7:
        return 'leve'  # Buraco pequeno e circular
    elif area_m2 > 0.15 or circularidade < 0.4:
        return 'grave'  # Grande ou muito irregular
    else:
        return 'media'
```

---

### 9. `tracker.py` - Rastreamento de Buracos (FASE 1) 🆕

**O que faz:** Rastreia buracos entre frames consecutivos para evitar salvar o mesmo buraco múltiplas vezes.

#### Problema que Resolve:

**Antes (sem tracker):**
```
Frame 1: Detecta buraco → Salva no banco (ID 1)
Frame 2: Detecta MESMO buraco → Salva de novo (ID 2) ❌
Frame 3: Detecta MESMO buraco → Salva de novo (ID 3) ❌
...
Resultado: 1 buraco = 30 registros! 😱
```

**Depois (com tracker):**
```
Frame 1: Detecta buraco → NOVO! Salva (Track ID 1) ✅
Frame 2: Detecta buraco → MESMO! Não salva ✅
Frame 3: Detecta buraco → MESMO! Não salva ✅
...
Resultado: 1 buraco = 1 registro! 🎉
```

#### Classe `BuracoTracker`

**Variáveis de Instância:**
```python
self.tracked_buracos = []      # Lista de buracos rastreados
self.iou_threshold = 0.3       # Limiar para considerar "mesmo buraco"
self.max_age_seconds = 5.0     # Tempo para esquecer buraco antigo
self.next_id = 1               # Próximo ID de track
```

**Método Principal: `update(detections)`**

**Entrada:**
```python
detections = [
    (x1, y1, x2, y2, conf, dist_m, width_m),
    (x1, y1, x2, y2, conf, dist_m, width_m),
    ...
]
```

**Saída:**
```python
(novos_buracos, buracos_atualizados)

novos_buracos = [
    {'track_id': 1, 'detection': (...), 'is_new': True},
    ...
]

buracos_atualizados = [
    {'track_id': 2, 'detection': (...), 'is_new': False, 'count': 5},
    ...
]
```

#### Algoritmo de Matching (IoU)

**IoU = Intersection over Union**

```
┌─────────┐
│ Bbox 1  │
│    ┌────┼────┐
│    │ IoU│    │
└────┼────┘    │
     │ Bbox 2  │
     └─────────┘

IoU = Área de Interseção / Área de União
```

**Cálculo de IoU:**
```python
def _calculate_iou(bbox1, bbox2):
    # Coordenadas da interseção
    x1_i = max(x1_bbox1, x1_bbox2)
    y1_i = max(y1_bbox1, y1_bbox2)
    x2_i = min(x2_bbox1, x2_bbox2)
    y2_i = min(y2_bbox1, y2_bbox2)
    
    # Área de interseção
    if x2_i < x1_i or y2_i < y1_i:
        intersection = 0
    else:
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
    
    # Área de união
    area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
    area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
    union = area1 + area2 - intersection
    
    return intersection / union
```

**Interpretação do IoU:**
- `IoU = 0.0` → Boxes não se tocam
- `IoU = 0.3` → Overlap pequeno (threshold padrão)
- `IoU = 0.5` → Overlap médio
- `IoU = 1.0` → Boxes idênticos

#### Lógica de Tracking:

```python
for cada_nova_detecção:
    melhor_match = None
    melhor_iou = 0
    
    for cada_track_existente:
        iou = calcular_iou(nova_detecção, track)
        
        if iou > threshold AND iou > melhor_iou:
            melhor_match = track
            melhor_iou = iou
    
    if melhor_match encontrado:
        # É o MESMO buraco!
        atualizar_track(melhor_match)
        adicionar_em_buracos_atualizados()
    else:
        # É um NOVO buraco!
        criar_novo_track()
        adicionar_em_novos_buracos()
```

#### Suavização de Posição

Quando um buraco é re-detectado, a posição é suavizada:

```python
def _smooth_bbox(old_bbox, new_bbox, alpha=0.7):
    # Média ponderada
    smoothed_x1 = 0.7 × new_x1 + 0.3 × old_x1
    smoothed_y1 = 0.7 × new_y1 + 0.3 × old_y1
    # ... (para todos os pontos)
    
    return smoothed_bbox
```

Isso evita "tremidas" na posição do box.

#### Limpeza Automática

Buracos que saem do campo de visão são removidos:

```python
def _remove_old_tracks(current_time):
    # Remove tracks não vistos há mais de 5 segundos
    self.tracked_buracos = [
        track for track in self.tracked_buracos
        if current_time - track['last_seen'] <= 5.0
    ]
```

---

## 🔄 Fluxo de Execução

### Inicialização (main.py)
```
1. Cria pastas necessárias
2. Inicializa banco de dados
3. Inicia LIDAR em background
4. Carrega modelo YOLO
5. Inicia câmera
6. Inicia gerenciador de câmera
7. Inicia detector
8. Inicia servidor web Flask
```

### Durante a Execução

**Thread 1: Captura de Câmera** (camera.py)
```
Loop infinito:
  1. Captura frame da câmera
  2. Converte formato de cor
  3. Pega informações de detecção atuais
  4. Desenha overlays (boxes, texto)
  5. Atualiza frame_global para stream
  6. Repete (~30 FPS)
```

**Thread 2: Detecção YOLO + Análise OpenCV + Tracking** (detector.py) 🆕
```
Loop infinito:
  1. Pega último frame capturado
  2. Redimensiona para 640x360
  3. Roda YOLO para detectar buracos
  4. Para cada buraco encontrado:
     - Calcula ângulo em relação à câmera
     - Busca distância no LIDAR
     - Estima largura do buraco
  5. Atualiza Tracker com detecções:
     - Compara com buracos já rastreados (IoU)
     - Identifica NOVOS vs ATUALIZADOS
  6. Para cada NOVO buraco:
     ✨ Análise OpenCV Completa:
     - Extrai contorno preciso
     - Calcula área, perímetro, circularidade
     - Converte pixels → metros
     - Analisa textura
     - Classifica severidade
     - Salva foto com anotações
     - Registra no banco com TODOS os dados
  7. Para buracos ATUALIZADOS:
     - Apenas atualiza display (não salva de novo)
  8. Atualiza estado para câmera desenhar
  9. Repete
```

**Diferença da Fase 1:**
- ✅ Tracker evita duplicatas no banco
- ✅ OpenCV extrai 20+ métricas por buraco
- ✅ Classificação automática de severidade
- ✅ Log detalhado no console

**Thread 3: Leitura LIDAR** (lidar_manager.py)
```
Loop infinito:
  1. Conecta ao LIDAR
  2. Para cada varredura 360°:
     - Agrupa leituras por setor de 5°
     - Guarda menor distância de cada setor
     - Atualiza dicionário de dados
  3. Se desconectar, tenta reconectar
  4. Repete continuamente
```

**Thread 4: Servidor Web** (api.py)
```
Aguarda requisições HTTP:
  - GET / → Página inicial
  - GET /video_feed → Stream de vídeo
  - GET /api/detections/recent → Últimas detecções
  - GET /api/lidar/latest → Dados do LIDAR
  - GET /deteccoes/<foto> → Imagem específica
```

---

## 📊 Variáveis Importantes

### Configurações Gerais
```python
screenshot_dir = '/home/suple/Desktop/suple360v2/deteccoes'  # Pasta de fotos
db_path = 'deteccoes/detections.db'                          # Arquivo do banco
```

### Câmera
```python
camera_resolution = (1280, 720)     # Resolução HD
detection_resolution = (640, 360)   # Resolução para YOLO (mais rápido)
cam_hfov_deg = 70.0                 # Campo de visão horizontal
```

### LIDAR
```python
LIDAR_PORT = "/dev/ttyUSB0"    # Porta USB
LIDAR_BAUD = 115200            # Taxa de comunicação
LIDAR_SECTOR_DEG = 5           # Tamanho de cada setor angular
```

### Servidor Web
```python
FLASK_HOST = '0.0.0.0'         # Aceita conexões de qualquer IP
FLASK_PORT = 5000              # Porta HTTP
```

### Modelo YOLO
```python
model_path = '/home/suple/Desktop/suple360v2/model/best.pt'
```

### Detecção
```python
detection_boxes = [
    (x1, y1, x2, y2, conf, dist_m, width_m),
    ...
]
```
Onde:
- `x1, y1`: canto superior esquerdo
- `x2, y2`: canto inferior direito
- `conf`: confiança (0.0 a 1.0)
- `dist_m`: distância em metros
- `width_m`: largura estimada em metros

---

## 🎓 Conceitos Importantes

### Threading (Multithreading)
- Permite executar várias tarefas simultaneamente
- Cada `Thread` roda um loop independente
- `daemon=True`: thread morre com o programa principal
- `lock`: previne conflitos ao acessar variáveis compartilhadas

### Lock (Sincronização)
```python
with lock:
    # Código protegido
    # Apenas uma thread pode executar por vez
```

### Coordenadas de Imagem
```
(0,0) -------- x (largura) -----→
  |
  |
  y (altura)
  |
  ↓
```
- Origem (0,0) no canto superior esquerdo
- X cresce para a direita
- Y cresce para baixo

### Bounding Box (Caixa Delimitadora)
```
(x1, y1) ┌─────────┐
         │         │
         │ BURACO  │
         │         │
         └─────────┘ (x2, y2)
```

### Conversão de Ângulos
```python
# Posição no frame → Ângulo relativo à câmera
x_center = (x1 + x2) / 2.0           # Centro do objeto
rel = (x_center / frame_width) - 0.5 # -0.5 (esquerda) a 0.5 (direita)
angle_deg = rel * cam_hfov_deg       # Ângulo em graus
```

**Exemplo:**
- Frame: 1280 pixels de largura
- Câmera: 70° de campo de visão
- Buraco no centro (x=640): `angle = 0°`
- Buraco na direita (x=1280): `angle = 35°`
- Buraco na esquerda (x=0): `angle = -35°`

---

## 🚀 Como Usar

### Iniciar o Sistema
```bash
cd /home/suple/Desktop/suple360v2
./run.sh
```

### Acessar Interface Web
```
http://localhost:5000
```

### Ver Detecções Recentes (API)
```
http://localhost:5000/api/detections/recent
```

### Ver Dados do LIDAR (API)
```
http://localhost:5000/api/lidar/latest
```

---

## 🔧 Manutenção

### Onde os dados são salvos?
- **Fotos:** `/home/suple/Desktop/suple360v2/deteccoes/`
- **Banco:** `/home/suple/Desktop/suple360v2/deteccoes/detections.db`

### Limpar histórico
```
POST http://localhost:5000/api/clear-history
```

### Logs importantes
```python
print("✓ Buraco detectado!")              # Nova detecção
print("[LIDAR] Conectado e operacional")  # LIDAR OK
print("✅ [DB] Detecção salva no banco")  # Salvo no DB
```

---

## 📝 Resumo

Este sistema é um **MVP (Minimum Viable Product)** que demonstra:
- ✅ Captura de vídeo em tempo real
- ✅ Detecção de objetos com IA (YOLO)
- ✅ Fusão de sensores (câmera + LIDAR)
- ✅ Persistência de dados (SQLite)
- ✅ Interface web (Flask)
- ✅ Arquitetura modular e extensível
- 🆕 **Análise geométrica avançada (OpenCV)**
- 🆕 **Tracking inteligente (evita duplicatas)**
- 🆕 **Classificação automática de severidade**

Cada módulo é independente e pode ser melhorado/testado separadamente!

---

## 🆕 Novidades da Fase 1 (OpenCV + Tracking)

### Dados Coletados por Buraco

**Antes da Fase 1:**
```json
{
  "bbox": [100, 150, 300, 280],
  "confianca": 0.94,
  "distancia_m": 2.3,
  "largura_m": 0.45
}
```
**Total: 7 campos**

---

**Depois da Fase 1:**
```json
{
  "track_id": 1,
  "bbox": [100, 150, 300, 280],
  "confianca": 0.94,
  "distancia_m": 2.3,
  
  "dimensoes_reais": {
    "largura_m": 0.452,
    "altura_m": 0.321,
    "area_m2": 0.1145,
    "perimetro_m": 1.423
  },
  
  "geometria": {
    "aspect_ratio": 1.18,
    "circularidade": 0.82,
    "convexidade": 0.91,
    "orientacao_deg": 23.4
  },
  
  "textura": {
    "intensidade_media": 87.3,
    "desvio_padrao": 24.1,
    "contraste": 0.68
  },
  
  "classificacao": {
    "severidade": "media",
    "prioridade": "media",
    "necessita_reparo": true
  }
}
```
**Total: 21 campos** 🎉

---

### Benefícios Imediatos

#### 1. Evita Duplicatas
```
Antes: 1 buraco = 30 registros no banco ❌
Depois: 1 buraco = 1 registro no banco ✅
```

#### 2. Dados Mais Ricos
```
Antes: "Buraco detectado com 94% de confiança"
Depois: "Buraco de 0.11 m², severidade MÉDIA, 
         circularidade 0.82, necessita reparo"
```

#### 3. Priorização Automática
```sql
-- Buscar buracos graves que precisam reparo urgente
SELECT * FROM buracos 
WHERE severidade = 'grave' 
  AND prioridade = 'alta'
ORDER BY area_m2 DESC;
```

#### 4. Análises Estatísticas
```python
# Tamanho médio dos buracos
SELECT AVG(area_m2) FROM buracos;

# Buracos mais circulares vs irregulares
SELECT severidade, AVG(circularidade) 
FROM buracos 
GROUP BY severidade;
```

---

### Exemplo de Log Detalhado

```
============================================================
✓ NOVO BURACO DETECTADO! Foto 1
============================================================

Buraco #1 (Track ID: 1):
  Área: 0.1145 m²
  Dimensões: 0.45m x 0.32m
  Circularidade: 0.82
  Severidade: MEDIA

============================================================
```

---

## 🎓 Conceitos Aprendidos na Fase 1

### 1. IoU (Intersection over Union)
- Métrica para comparar sobreposição de bounding boxes
- Usado no tracking para identificar "mesmo buraco"
- Valores de 0 (sem overlap) a 1 (idênticos)

### 2. Segmentação de Imagem
- Separar objeto (buraco) do fundo (asfalto)
- Usa threshold adaptativo para lidar com iluminação variável
- Resulta em contorno preciso do buraco

### 3. Análise de Contornos
- `cv2.contourArea()` - área exata ocupada
- `cv2.arcLength()` - perímetro do contorno
- `cv2.fitEllipse()` - ajusta elipse ao formato

### 4. Descritores de Forma
- **Circularidade**: O quão próximo de um círculo
- **Convexidade**: O quão irregular é a borda
- **Aspect Ratio**: Relação entre largura e altura

### 5. Tracking Multi-Objeto
- Manter identidade de objetos entre frames
- Suavização de posição (evita tremidas)
- Remoção automática de tracks antigos

---

**Criado em:** Janeiro 2026  
**Versão:** 2.1 (Fase 1 - OpenCV + Tracking)  
**Próxima Fase:** Mapeamento 2D Bird's Eye View


---

## 🗺️ Fase 2: Mapeamento 2D (Bird's Eye View)

### Módulos Adicionados:
- **mapper.py** - Construtor de mapas 2D top-down
- **map_utils.py** - Conversões de coordenadas
- **templates/map.html** - Interface web do mapa

### Funcionalidades:
✅ Mapa 20x20 metros (800x800 pixels)  
✅ Plotagem de buracos com cores por severidade  
✅ Visualização de LIDAR 360°  
✅ Exportação para PNG  
✅ Interface web com auto-atualização  

### Acessar:
http://localhost:5000/map

### Para mais detalhes:
Ver arquivo **FASE2_RESUMO.md** para documentação completa.

---

**Versão:** 2.2 (Fase 2 - Mapeamento 2D)  
**Última Atualização:** 06/Janeiro/2026

---

## 🔬 Fase 3: Calibração e Profundidade

### Módulos Adicionados:
- **calibration.py** - Calibração de câmera com padrão xadrez
- **depth_estimator.py** - Estimativa de profundidade monocular
- Atualizado **opencv_analyzer.py** - Integração com profundidade
- Atualizado **database.py** - 6 novos campos de profundidade

### Funcionalidades:
✅ Calibração precisa da câmera (matriz intrínseca, distorção)  
✅ Estimativa de profundidade usando Shape from Shading  
✅ Análise de gradientes, sombras e intensidade  
✅ Classificação: raso (<3cm), médio (3-8cm), profundo (>8cm)  
✅ Novos campos no banco: gradiente, sombra, score, profundidade  
✅ Scripts de calibração e teste  

### Como Calibrar a Câmera:

**1. Prepare o padrão xadrez:**
```bash
# Imprima um padrão xadrez 9x6 (disponível online)
# Cada quadrado deve ter 2.5cm x 2.5cm
```

**2. Tire fotos do padrão:**
```bash
# Crie pasta para imagens de calibração
mkdir calibracao

# Tire 15-20 fotos do padrão em diferentes ângulos
# Certifique-se que o padrão está completamente visível
```

**3. Execute calibração:**
```bash
python3 calibrate_camera.py --images calibracao/*.jpg
```

**4. Resultado:**
```
✅ Calibração concluída!
💾 Arquivo salvo: camera_calibration.pkl
📊 Erro de reprojeção: 0.31 pixels
```

### Como Funciona a Estimativa de Profundidade:

**1. Análise de Gradientes (40% do score):**
- Calcula variação de intensidade usando Sobel
- Buracos profundos têm bordas mais acentuadas
- Gradiente médio > 35 = profundo

**2. Análise de Sombras (30% do score):**
- Mede porcentagem de pixels escuros
- Buracos profundos acumulam sombra interna
- Usa threshold adaptativo (Otsu)

**3. Variação de Intensidade (30% do score):**
- Compara brilho da borda vs centro
- Centro mais escuro indica maior profundidade
- Diferença > 50 = profundo

**4. Estimativa em Centímetros:**
```python
# Score 0-100 → 0.5cm a 10cm
# Ajustado pela distância do LIDAR
profundidade_cm = 0.5 + (score/100) * 9.5
```

### Novos Campos no Banco de Dados:

```sql
-- 6 novos campos na tabela buracos:
gradiente_medio REAL,           -- Intensidade do gradiente (0-255)
intensidade_sombra REAL,        -- % de pixels escuros (0-100)
variacao_intensidade REAL,      -- Diferença borda-centro (0-255)
profundidade_score REAL,        -- Score combinado (0-100)
profundidade_cm REAL,           -- Profundidade estimada em cm
classificacao_profundidade TEXT -- 'raso', 'medio', 'profundo'
```

### Consultar Dados de Profundidade:

```python
import sqlite3

conn = sqlite3.connect('deteccoes/detections.db')
cursor = conn.cursor()

# Busca buracos profundos
cursor.execute('''
    SELECT 
        area_m2, 
        profundidade_cm, 
        classificacao_profundidade,
        severidade
    FROM buracos
    WHERE classificacao_profundidade = 'profundo'
    ORDER BY profundidade_cm DESC
''')

for row in cursor.fetchall():
    area, prof, classif, sev = row
    print(f"Buraco {sev}: {area:.4f}m² - {prof:.2f}cm ({classif})")
```

### Scripts Auxiliares:

**1. calibrate_camera.py:**
```bash
# Calibra câmera e salva parâmetros
python3 calibrate_camera.py --images calibracao/*.jpg
```

**2. test_fase3.py:**
```bash
# Testa todos os componentes da Fase 3
python3 test_fase3.py
```

### Exemplo de Resultado:

```
📊 Buraco detectado:
   Área: 0.0823 m²
   Dimensões: 0.35m x 0.28m
   
   🔬 Profundidade:
      Gradiente: 42.15
      Sombra: 68.5%
      Variação: 51.2
      Score: 73.8/100
      Profundidade: 7.5 cm
      Classificação: médio
   
   ⚠️ Severidade: media
   📍 Prioridade: media
```

### Para mais detalhes:
Ver arquivo **FASE3_RESUMO.md** para documentação completa.

---

**Versão:** 2.3 (Fase 3 - Calibração + Profundidade)  
**Última Atualização:** 06/Janeiro/2026

---

## 🎨 Fase 4: Análise Avançada de Textura

### Módulos Adicionados:
- **texture_analyzer.py** - Análise GLCM, entropia, FFT (499 linhas)
- **damage_classifier.py** - Classificação de tipo de dano (320 linhas)
- Atualizado **opencv_analyzer.py** - Integração completa
- Atualizado **database.py** - 6 novos campos de textura

### Funcionalidades:
✅ Análise GLCM (Gray-Level Co-occurrence Matrix)  
✅ Entropia de Shannon (medida de desordem)  
✅ Análise de frequências (FFT 2D)  
✅ Histogramas RGB e HSV  
✅ Densidade de bordas (Canny)  
✅ Classificação de textura: lisa, rugosa, irregular, complexa  
✅ Classificação de dano: buraco circular/irregular, rachadura, erosão  

### Análise GLCM:

A **GLCM** analisa relação espacial entre pixels vizinhos:

```python
# 4 métricas principais:
- Energia: Uniformidade da textura (0-1)
- Homogeneidade: Suavidade da textura (0-1)
- Contraste: Variação local (0-∞)
- Correlação: Dependência linear (-1 a 1)
```

**Exemplo de uso:**
```python
from src.texture_analyzer import TextureAnalyzer

analyzer = TextureAnalyzer()
resultado = analyzer.analisar_textura_avancada(roi, contorno)

print(f"Entropia: {resultado['entropia']:.3f}")          # 0-8
print(f"Energia: {resultado['energia']:.3f}")            # 0-1
print(f"Homogeneidade: {resultado['homogeneidade']:.3f}")# 0-1
print(f"Textura: {resultado['textura_dominante']}")      # lisa/rugosa/irregular/complexa
```

### Classificação de Tipo de Dano:

O sistema detecta 4 tipos de danos:

| Tipo | Critérios | Características |
|------|-----------|-----------------|
| **Buraco Circular** | Circularidade > 0.65, Convexidade > 0.80 | Compacto, forma regular |
| **Buraco Irregular** | Circularidade < 0.60, Entropia alta | Bordas complexas, irregular |
| **Rachadura** | Aspect ratio > 3.0, Skeleton alongado | Linear, fino, alongado |
| **Erosão** | Área < 0.08 m², Bordas difusas | Superficial, disperso |

**Exemplo de uso:**
```python
from src.damage_classifier import DamageClassifier

classifier = DamageClassifier()
resultado = classifier.classificar_dano(roi, contorno, geometria, textura, dimensoes)

print(f"Tipo: {resultado['tipo_dano']}")                    # buraco_circular
print(f"Confiança: {resultado['confianca']:.1f}%")          # 85.3%
print(f"Descrição: {resultado['caracteristicas']}")         # "Buraco compacto..."
```

### Métricas de Textura:

**1. Entropia de Shannon:**
```python
# Mede complexidade/desordem da textura
Entropia = -Σ(p * log2(p))

- Baixa (< 4.0): Textura uniforme, lisa
- Média (4.0-6.0): Textura rugosa
- Alta (> 6.0): Textura irregular, complexa
```

**2. Análise de Frequências (FFT):**
```python
# Detecta padrões repetitivos
- Alta frequência dominante: Textura detalhada/rugosa
- Baixa frequência: Textura lisa/uniforme
- Rugosidade: % de energia em altas frequências
```

**3. Densidade de Bordas:**
```python
# Porcentagem de pixels de borda (Canny)
- < 10%: Textura lisa
- 10-30%: Textura rugosa
- > 30%: Textura irregular
```

### Novos Campos no Banco de Dados:

```sql
-- 6 novos campos na tabela buracos:
entropia REAL,                -- Entropia de Shannon (0-8)
energia_glcm REAL,            -- Uniformidade GLCM (0-1)
homogeneidade_glcm REAL,      -- Suavidade GLCM (0-1)
densidade_bordas REAL,        -- % de bordas (0-100)
tipo_dano TEXT,               -- Tipo classificado
tipo_dano_confianca REAL      -- Confiança da classificação (0-100)
```

### Consultar Dados por Tipo de Dano:

```python
import sqlite3

conn = sqlite3.connect('deteccoes/detections.db')
cursor = conn.cursor()

# Busca rachaduras detectadas
cursor.execute('''
    SELECT 
        area_m2,
        aspect_ratio,
        tipo_dano,
        tipo_dano_confianca,
        severidade
    FROM buracos
    WHERE tipo_dano = 'rachadura'
    ORDER BY tipo_dano_confianca DESC
''')

for row in cursor.fetchall():
    area, asp, tipo, conf, sev = row
    print(f"Rachadura {sev}: {area:.4f}m² (asp={asp:.2f}) - {conf:.1f}% confiança")
```

### Exemplo de Resultado Completo:

```
📊 Buraco detectado:
   Dimensões: 0.35m x 0.28m (0.0823 m²)
   
   🎨 Textura Básica:
      Intensidade: 87.3
      Desvio padrão: 24.1
      Contraste: 0.68
   
   🔬 Textura Avançada (Fase 4):
      Entropia: 5.23
      Energia: 0.31
      Homogeneidade: 0.58
      Contraste GLCM: 142.5
      Densidade bordas: 28.3%
      Textura dominante: rugosa
   
   🔍 Tipo de Dano (Fase 4):
      Tipo: buraco_irregular
      Confiança: 78.5%
      Tipo secundário: None
      Descrição: Buraco irregular (circ=0.42), bordas complexas
   
   🔬 Profundidade:
      Profundidade: 7.5 cm
      Classificação: médio
   
   ⚠️ Severidade: media
   📍 Prioridade: media
```

### Scripts de Teste:

```bash
# Testa análise de textura avançada
python3 test_fase4.py
```

**Saída esperada:**
```
✅ TESTE 1: Análise de Textura Avançada
   Entropia: 0.926
   Homogeneidade: 0.966
   Textura dominante: lisa

✅ TESTE 2: Classificação de Tipo de Dano
   CIRCULAR: buraco_circular (100.0%)
   IRREGULAR: buraco_irregular (80.0%)
   RACHADURA: rachadura (90.0%)
   EROSAO: erosao (70.0%)

✅ TESTE 3: Integração Completa
   Todos os módulos funcionando ✓
```

### Para mais detalhes:
Ver arquivo **FASE4_RESUMO.md** para documentação completa.

---

**Versão:** 2.4 (Fase 4 - Análise Avançada de Textura)  
**Última Atualização:** 06/Janeiro/2026

---

## ⚡ Fase 5: Otimização de Performance

### Módulos Adicionados:
- **roi_detector.py** - Detecção de ROI (Region of Interest) (165 linhas)
- **motion_detector.py** - Detecção de movimento (175 linhas)
- **performance_optimizer.py** - Multi-threading e pipeline otimizado (230 linhas)

### Funcionalidades:
✅ ROI Detection: 4 modos (full, bottom_half, bottom_two_thirds, adaptive)  
✅ Motion Detection: 2 métodos (frame_diff, mog2)  
✅ Multi-threading: Workers paralelos com fila assíncrona  
✅ Adaptive Frame Skipping: Mantém FPS alvo  
✅ Métricas em tempo real: FPS, skip rate, processing time  

### Speedup Alcançado:

| Otimização | Speedup | Descrição |
|------------|---------|-----------|
| Baseline | 1.0x | Sem otimização |
| ROI Detection | 2.0x | Processa só metade inferior |
| Motion Detection | **18x** | Pula frames estáticos |
| **Combinado** | **20x** | ROI + Motion juntos |

### 1. ROI Detection (Region of Interest):

**Problema:** Processar frame completo desperdiça recursos (buracos não aparecem no céu).

**Solução:** Processar apenas região relevante.

**Modos disponíveis:**

```python
from src.roi_detector import ROIDetector

# Modo 1: Metade inferior (50% redução, 2x speedup)
detector = ROIDetector(roi_mode='bottom_half')
roi, bbox = detector.get_roi(frame)

# Modo 2: 2/3 inferiores (33% redução, 1.5x speedup)
detector = ROIDetector(roi_mode='bottom_two_thirds')

# Modo 3: Adaptativo (detecta asfalto automaticamente)
detector = ROIDetector(roi_mode='adaptive')

# Modo 4: Completo (sem otimização)
detector = ROIDetector(roi_mode='full')
```

**Uso com detector:**
```python
# Extrai ROI
roi, roi_bbox = detector.get_roi(frame)

# Detecta buracos na ROI
boxes = yolo_detector.detect(roi)

# Ajusta coordenadas para frame original
for box in boxes:
    adjusted_box = detector.adjust_bbox_to_original(box, roi_bbox)
```

### 2. Motion Detection:

**Problema:** Processar frames idênticos (veículo parado) desperdiça recursos.

**Solução:** Detectar movimento e pular frames estáticos.

**Métodos disponíveis:**

```python
from src.motion_detector import MotionDetector

# Método 1: Frame Differencing (rápido)
detector = MotionDetector(method='frame_diff', threshold=0.02)

# Método 2: Background Subtraction MOG2 (preciso)
detector = MotionDetector(method='mog2', threshold=0.02)

# Verifica movimento
has_motion, score = detector.has_motion(frame)

if has_motion:
    # Processa frame
    result = process_frame(frame)
else:
    # Pula frame (economiza recursos)
    pass
```

**Estatísticas:**
```python
stats = detector.get_stats()
print(f"Taxa de pulo: {stats['skip_rate']:.1f}%")
print(f"Speedup estimado: {stats['estimated_speedup']:.2f}x")
```

### 3. Multi-threading:

**Problema:** Processamento sequencial subutiliza CPU multi-core.

**Solução:** Pipeline com workers paralelos.

```python
from src.performance_optimizer import PerformanceOptimizer

def process_function(frame):
    # Sua função de processamento
    return yolo.detect(frame)

# Cria otimizador com 2 workers
optimizer = PerformanceOptimizer(
    process_func=process_function,
    max_queue_size=5,
    num_workers=2
)

optimizer.start()

# Submete frames
for i, frame in enumerate(frames):
    optimizer.submit_frame(frame, i)

# Pega resultados
result = optimizer.get_result(timeout=0.1)
if result:
    frame_id, detection, processing_time = result

optimizer.stop()
```

### 4. Adaptive Frame Skipping:

**Problema:** Câmera captura 30 FPS mas processamento é 10 FPS.

**Solução:** Pular frames adaptativamente para manter FPS alvo.

```python
from src.performance_optimizer import AdaptiveFrameSkipper

# Mantém 10 FPS
skipper = AdaptiveFrameSkipper(target_fps=10)

while True:
    frame = camera.read()
    
    if skipper.should_process():
        # Processa frame
        result = process(frame)
    else:
        # Pula frame
        continue
```

### Benchmark Completo:

```
📊 RESULTADOS:
  Sem otimização:     1.51s  (33 FPS)   [baseline]
  Com ROI:            1.51s  (33 FPS)   [1.0x]
  Com Motion:         0.08s  (606 FPS)  [18x] ⚡
  Com TUDO:           0.07s  (681 FPS)  [20x] 🚀
```

**Interpretação:**
- ROI sozinho: não melhora muito (frames já tinham movimento)
- Motion Detection: **18x mais rápido** (pula 98% dos frames estáticos)
- Combinado: **20x mais rápido** (economia máxima)

### Configuração Recomendada:

**Para veículo em movimento:**
```python
roi = ROIDetector(roi_mode='bottom_half')          # 2x speedup
motion = MotionDetector(method='frame_diff', threshold=0.02)  # 18x speedup
```

**Para veículo frequentemente parado:**
```python
roi = ROIDetector(roi_mode='bottom_two_thirds')    # 1.5x speedup
motion = MotionDetector(method='mog2', threshold=0.01)  # Mais sensível
```

### Métricas em Tempo Real:

```python
# ROI Detector
print(f"Speedup estimado: {roi.estimate_speedup():.1f}x")

# Motion Detector
stats = motion.get_stats()
print(f"Taxa de pulo: {stats['skip_rate']:.1f}%")
print(f"Speedup: {stats['estimated_speedup']:.2f}x")

# Performance Optimizer
metrics = optimizer.get_metrics()
print(f"FPS: {metrics['fps']:.1f}")
print(f"Tempo médio: {metrics['avg_processing_time_ms']:.1f}ms")
print(f"Fila: {metrics['queue_size']}")
```

### Scripts de Teste:

```bash
# Testa otimizações e roda benchmark
python3 test_fase5.py
```

**Saída esperada:**
```
✅ TESTE 1: ROI Detector
   bottom_half: 50% redução, 2.0x speedup

✅ TESTE 2: Motion Detector
   Taxa de pulo: 98.0%
   Speedup: 50.00x (frames estáticos)

✅ TESTE 3: Multi-threading
   FPS: 1.0, Tempo médio: 30.1ms

✅ TESTE 4: Adaptive Frame Skipper
   5 FPS: 83% pulo
   10 FPS: 66% pulo
   15 FPS: 50% pulo

📊 BENCHMARK:
   Speedup combinado: 20.53x 🚀
```

### Quando Usar Cada Otimização:

| Cenário | ROI | Motion | Multi-thread |
|---------|-----|--------|--------------|
| Veículo em movimento constante | ✅ | ❌ | ✅ |
| Veículo parado frequentemente | ✅ | ✅✅ | ✅ |
| Processamento pesado (YOLO + análise completa) | ✅ | ✅ | ✅✅ |
| Hardware limitado (Raspberry Pi) | ✅✅ | ✅ | ❌ |

### Para mais detalhes:
Ver arquivo **FASE5_RESUMO.md** para documentação completa.

---

**Versão:** 2.5 (Fase 5 - Otimização de Performance)  
**Última Atualização:** 06/Janeiro/2026

---

## 📐 Fase 6: Sistema de Calibração Completo

### Módulos Adicionados:
- **pattern_generator.py** - Geração de padrões de calibração (PDF) (310 linhas)
- **templates/calibracao.html** - Interface para gerar PDFs (350 linhas)
- **templates/calibracao_live.html** - Calibração em tempo real (600 linhas)
- Atualizado **api.py** - 8 novas rotas de calibração

### Funcionalidades:
✅ Geração de padrões xadrez 9×6 em PDF (25mm por quadrado)  
✅ Geração de markers ArUco em PDF (DICT_6X6_250, 100mm)  
✅ Interface web para download de PDFs  
✅ Calibração em tempo real com stream de vídeo  
✅ Detecção automática de padrões (xadrez e ArUco)  
✅ Captura de múltiplas fotos (mín. 10, rec. 15-20)  
✅ Cálculo de matriz intrínseca e coeficientes de distorção  
✅ Salvamento de calibrações (.npz)  
✅ Visualização de calibrações salvas  

---

### 1. O que é Calibração de Câmera?

**Calibração** é o processo de medir os **parâmetros internos** da câmera para:

**a) Corrigir distorções da lente:**
```
Antes:                 Depois:
┌──────────┐          ┌──────────┐
│  ╱────╲  │          │  ┌────┐  │
│ (  □  ) │    →     │  │  □  │  │  (linhas retas)
│  ╲────╱  │          │  └────┘  │
└──────────┘          └──────────┘
  (distorção)          (corrigido)
```

**b) Medir dimensões reais com precisão:**
```
Sem calibração:        Com calibração:
Buraco = "203 pixels"  Buraco = 0.452 m
(não sabe metros)      (medida exata!)
```

---

### 2. Matriz Intrínseca da Câmera

A calibração calcula a **matriz intrínseca** (3×3):

```python
K = [
    [fx,  0, cx],
    [ 0, fy, cy],
    [ 0,  0,  1]
]
```

**Parâmetros:**
- **fx, fy**: Distância focal (em pixels)
  - Controla o "zoom" da câmera
  - Típico: 500-1500 px para câmera Raspberry Pi
  
- **cx, cy**: Centro óptico (coordenadas do pixel central)
  - Idealmente no centro da imagem
  - Exemplo: (640, 360) para resolução 1280×720

**Coeficientes de Distorção:**
```python
dist = [k1, k2, p1, p2, k3]
```
- **k1, k2, k3**: Distorção radial (efeito "barril" ou "almofada")
- **p1, p2**: Distorção tangencial (desalinhamento da lente)

**Onde é usado:**
- Conversão pixel → metro (estimativa de tamanho real)
- Correção de distorção de imagem
- Mapeamento 3D preciso

---

### 3. Como Funciona a Calibração

#### **Etapa 1: Geração de Padrões**

**Acesse:** `http://localhost:5000/calibracao`

**Padrões disponíveis:**

**a) Xadrez 9×6 (Recomendado para iniciantes):**
- 9 cantos internos na horizontal
- 6 cantos internos na vertical
- 54 cantos totais para detecção
- Quadrados de 25mm × 25mm

**b) ArUco Markers (Recomendado para precisão):**
- 10 markers únicos (IDs 0-9)
- Dicionário: DICT_6X6_250
- Tamanho: 100mm × 100mm
- Precisão 4-6x melhor que xadrez

**Como gerar:**
```python
# Backend (pattern_generator.py)
from pattern_generator import CalibrationPatternGenerator

generator = CalibrationPatternGenerator()

# Gera xadrez
generator.gerar_padrao_xadrez(
    pattern_size=(9, 6),      # 9×6 cantos
    square_size_mm=25,        # 25mm por quadrado
    output_path='xadrez.pdf'
)

# Gera ArUco
generator.gerar_aruco_markers(
    num_markers=10,           # 10 markers
    marker_size_mm=100,       # 100mm de tamanho
    output_path='aruco.pdf'
)
```

**Clique nos botões da interface:**
- 📥 Baixar Padrão Xadrez
- 📥 Baixar Markers ArUco

---

#### **Etapa 2: Impressão e Preparação**

**Instruções críticas:**

1. **Imprima em A4** sem escalar (100% do tamanho)
2. **Cole em superfície rígida** (papelão, placa de isopor)
3. **Certifique-se que está plano** (sem dobras ou curvas)
4. **Meça o tamanho real** com régua:
   - Xadrez: cada quadrado deve ter ~25mm
   - ArUco: cada marker deve ter ~100mm

**Por que a precisão importa?**
```
Erro de 1mm na impressão = erro de 5-10cm na medição final!
```

---

#### **Etapa 3: Calibração em Tempo Real**

**Acesse:** `http://localhost:5000/calibracao_live`

**Interface:**

```
┌─────────────────────────────────────────────┐
│  📹 Visualização da Câmera                   │
│  ┌───────────────────────────────────────┐  │
│  │   [Stream com overlay de detecção]    │  │
│  │   ✓ Padrão detectado! | 54 cantos     │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  ⚙️ Configurações                            │
│  Tipo: [Xadrez 9×6 ▼]                      │
│                                             │
│  📊 Estatísticas                             │
│  Fotos: 12     Taxa: 85%                    │
│  Qualidade: ████████░░ 80%                  │
│                                             │
│  📸 [Capturar Frame]  🎯 [Calibrar]         │
│  🔄 [Resetar]                               │
│                                             │
│  📊 Resultados:                              │
│  Erro: 0.42 px | Focal: 1234.5 px          │
└─────────────────────────────────────────────┘
```

**Elementos da tela:**

**1. Taxa de Detecção (0-100%):**
```python
# Mede: quantos frames detectam o padrão
taxa = (frames_detectados / frames_totais) × 100%

# Interpretação:
> 80% = Ótimo! Padrão bem posicionado ✅
50-80% = Razoável, ajuste ângulo ⚠️
< 50% = Ruim, padrão não está visível ❌
```

**2. Qualidade da Imagem (barra colorida):**
```python
# Xadrez: quantos cantos foram detectados
qualidade = (cantos_detectados / 54) × 100%

# ArUco: quantos markers foram detectados  
qualidade = (markers_detectados / 10) × 100%

# Cores:
🟢 Verde (70-100%): Capture agora!
🟡 Amarelo (40-70%): Ajuste posição
🔴 Vermelho (0-40%): Padrão parcial
```

**3. Botão "Capturar Frame":**
```python
# O que faz:
1. Verifica se padrão está detectado
2. Salva frame + coordenadas dos cantos/markers
3. Incrementa contador de fotos
4. Mostra alerta de sucesso

# Quando usar:
- Status: "Padrão detectado!" (luz verde)
- Qualidade: > 70% (barra verde)
- Ângulo diferente das fotos anteriores
```

**4. Botão "Calibrar" (mín. 10 fotos):**
```python
# Requisitos:
- Mínimo: 10 fotos capturadas
- Recomendado: 15-20 fotos
- Variedade de ângulos

# O que faz:
1. Executa cv2.calibrateCamera() ou cv2.aruco.calibrateCameraAruco()
2. Calcula matriz intrínseca K
3. Calcula coeficientes de distorção
4. Calcula erro de reprojeção
5. Salva em .npz

# Resultado:
{
    "reprojection_error": 0.42,  # px (quanto menor melhor)
    "focal_x": 1234.5,           # px
    "focal_y": 1236.8,           # px
    "center_x": 640.2,           # px
    "center_y": 359.8,           # px
    "calibration_file": "calibracao_chessboard.npz"
}
```

---

#### **Etapa 4: Como Capturar Fotos Corretamente**

**Objetivo:** Cobrir diferentes ângulos e distâncias para calibração robusta.

**Estratégia recomendada (15-20 fotos):**

```
Vista Superior:

Posição 1-4: Centro em diferentes distâncias
   🎯        🎯      🎯    🎯
  perto    médio   médio  longe

Posição 5-8: Ângulos inclinados
   🎯        🎯      🎯    🎯
  ↗30°     ↖30°    ↘30°  ↙30°

Posição 9-12: Cantos da imagem
   🎯                    🎯
  canto               canto
  sup-esq            sup-dir

   🎯                    🎯
  canto               canto
  inf-esq            inf-dir

Posição 13-16: Rotação do padrão
   📄        📄      📄    📄
  0°       45°     90°   135°

Posição 17-20: Variações de iluminação
   🔆 luz   ☀️ sol  🌙 sombra  💡 lateral
```

**Dicas:**
- ✅ Sempre mantenha o padrão **completamente visível**
- ✅ Varie **ângulo, distância e rotação**
- ✅ Capture em **diferentes iluminações**
- ❌ Não capture fotos muito similares (desperdício)
- ❌ Não cubra parte do padrão com a mão
- ❌ Não capture com padrão dobrado/amassado

---

#### **Etapa 5: Executar Calibração**

**Backend (api.py):**

```python
@app.route('/api/calibracao_executar', methods=['POST'])
def calibracao_executar():
    # 1. Verifica mínimo de 10 fotos
    if len(calibration_images) < 10:
        return error("Mínimo 10 fotos")
    
    # 2. Monta pontos 3D (mundo real)
    objpoints = []  # Coordenadas 3D reais (0,0,0), (25mm,0,0), ...
    imgpoints = []  # Coordenadas 2D na imagem (pixels)
    
    for img_data in calibration_images:
        objpoints.append(objp)          # Padrão conhecido
        imgpoints.append(img_data['corners'])  # Cantos detectados
    
    # 3. Calibra câmera
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, (w, h), None, None
    )
    
    # 4. Calcula erro de reprojeção
    mean_error = 0
    for i in range(len(objpoints)):
        # Projeta pontos 3D de volta para 2D
        imgpoints2, _ = cv2.projectPoints(
            objpoints[i], rvecs[i], tvecs[i], mtx, dist
        )
        # Calcula diferença entre real e projetado
        error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
        mean_error += error
    mean_error /= len(objpoints)
    
    # 5. Salva resultado
    np.savez(
        'calibracao_chessboard.npz',
        camera_matrix=mtx,
        dist_coeffs=dist,
        pattern_type='chessboard',
        num_images=len(calibration_images),
        timestamp=int(time.time())
    )
    
    return jsonify({
        "reprojection_error": mean_error,
        "focal_x": float(mtx[0, 0]),
        "focal_y": float(mtx[1, 1]),
        ...
    })
```

---

#### **Etapa 6: Interpretação de Resultados**

**Erro de Reprojeção:**

```python
# Quanto menor, melhor a calibração
< 0.5 px   = Excelente! ✅✅✅
0.5-1.0 px = Bom ✅✅
1.0-2.0 px = Aceitável ✅
> 2.0 px   = Ruim, recalibre ❌
```

**O que significa?**
- Erro de 0.5 px = ao reprojetar pontos 3D, eles ficam 0.5 pixels distantes do esperado
- Erro alto = calibração imprecisa, medições erradas

**Como melhorar:**
1. Tire mais fotos (20-25)
2. Cubra mais ângulos diferentes
3. Use padrão ArUco (mais preciso)
4. Certifique-se que padrão está plano
5. Use boa iluminação (sem sombras)

**Parâmetros da Câmera:**

```python
# Exemplo de resultado:
Focal X: 1234.5 px
Focal Y: 1236.8 px
Centro: (640.2, 359.8)

# Validações:
✅ fx ≈ fy (diferença < 5%) = lente OK
❌ fx muito diferente de fy = lente defeituosa
✅ centro próximo de (640, 360) para 1280×720 = OK
❌ centro muito deslocado = câmera desalinhada
```

---

### 4. Onde as Calibrações são Salvas?

**Localização:**
```bash
/home/suple/Desktop/suple360v2/calibracao_chessboard.npz
/home/suple/Desktop/suple360v2/calibracao_aruco.npz
```

**Conteúdo do arquivo .npz:**

```python
import numpy as np

# Carregar calibração
data = np.load('calibracao_chessboard.npz')

# Acessar parâmetros
camera_matrix = data['camera_matrix']  # Matriz K 3×3
dist_coeffs = data['dist_coeffs']      # [k1, k2, p1, p2, k3]
pattern_type = data['pattern_type']    # 'chessboard' ou 'aruco'
num_images = data['num_images']        # Quantas fotos usadas
timestamp = data['timestamp']          # Unix timestamp

print(f"Câmera calibrada com {num_images} fotos")
print(f"Matriz intrínseca:\n{camera_matrix}")
print(f"Distorção: {dist_coeffs}")
```

---

### 5. Visualização de Calibrações Salvas

**Interface:** Na parte inferior de `/calibracao_live`

```
┌─────────────────────────────────────────────┐
│  💾 Calibrações Salvas                       │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 📐 Xadrez 9×6                        │   │
│  │ Erro: 0.42 px    Fotos: 15          │   │
│  │ Focal X: 1234.5  Focal Y: 1236.8    │   │
│  │ Centro: (640, 360)                   │   │
│  │ Data: 06/01/2026 14:32               │   │
│  │ [🗑️ Deletar]                        │   │
│  └─────────────────────────────────────┘   │
│                                             │
│  ┌─────────────────────────────────────┐   │
│  │ 📐 ArUco Markers                     │   │
│  │ Erro: 0.28 px    Fotos: 18          │   │
│  │ Focal X: 1235.2  Focal Y: 1237.1    │   │
│  │ Centro: (641, 359)                   │   │
│  │ Data: 06/01/2026 15:45               │   │
│  │ [🗑️ Deletar]                        │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

**Funcionalidades:**
- **Listar:** GET `/api/calibracao_listar`
  - Varre arquivos `.npz` no diretório
  - Lê metadados de cada calibração
  - Ordena por data (mais recente primeiro)

- **Deletar:** POST `/api/calibracao_deletar`
  - Remove arquivo `.npz` do disco
  - Atualiza lista automaticamente

**Backend:**

```python
@app.route('/api/calibracao_listar')
def calibracao_listar():
    calibrations = []
    
    for filepath in glob.glob('calibracao_*.npz'):
        data = np.load(filepath)
        calibrations.append({
            'filename': os.path.basename(filepath),
            'pattern_type': str(data['pattern_type']),
            'num_images': int(data['num_images']),
            'focal_x': float(data['camera_matrix'][0, 0]),
            'focal_y': float(data['camera_matrix'][1, 1]),
            'center_x': float(data['camera_matrix'][0, 2]),
            'center_y': float(data['camera_matrix'][1, 2]),
            'timestamp': int(data['timestamp'])
        })
    
    # Ordena por timestamp
    calibrations.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return jsonify({"calibrations": calibrations})
```

---

### 6. Como Usar a Calibração no Sistema

**Carregar calibração salva:**

```python
import numpy as np
import cv2

# Carrega parâmetros
data = np.load('calibracao_chessboard.npz')
camera_matrix = data['camera_matrix']
dist_coeffs = data['dist_coeffs']

# Corrige distorção de imagem
frame_undistorted = cv2.undistort(
    frame, camera_matrix, dist_coeffs
)

# Converte pixel → metro (usando distância do LIDAR)
def pixel_to_meter(bbox_width_px, distance_m):
    # FOV horizontal da câmera
    fov_rad = 2 * np.arctan(image_width / (2 * camera_matrix[0, 0]))
    
    # Largura real do campo de visão na distância D
    real_fov_width = 2 * distance_m * np.tan(fov_rad / 2)
    
    # Fator de conversão
    meters_per_pixel = real_fov_width / image_width
    
    # Largura real do buraco
    real_width_m = bbox_width_px * meters_per_pixel
    
    return real_width_m
```

**Integração com detector:**

```python
# Em opencv_analyzer.py
class OpenCVAnalyzer:
    def __init__(self, calibration_file=None):
        if calibration_file:
            data = np.load(calibration_file)
            self.camera_matrix = data['camera_matrix']
            self.dist_coeffs = data['dist_coeffs']
        else:
            self.camera_matrix = None
            self.dist_coeffs = None
    
    def analisar_buraco(self, frame, bbox, distancia_m):
        # Se calibrado, corrige distorção
        if self.camera_matrix is not None:
            frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
        
        # Usa calibração para medir com mais precisão
        if self.camera_matrix is not None and distancia_m:
            largura_real = self._pixel_to_meter_calibrated(
                bbox_width, distancia_m
            )
        else:
            largura_real = self._pixel_to_meter_estimated(
                bbox_width, distancia_m
            )
        
        return {
            'dimensoes_reais': {
                'largura_m': largura_real,
                ...
            }
        }
```

---

### 7. Comparação: Xadrez vs ArUco

| Aspecto | Xadrez 9×6 | ArUco Markers |
|---------|-----------|---------------|
| **Precisão** | ±3-8 cm | ±1-3 cm (4-6x melhor) |
| **Facilidade** | ✅✅✅ Fácil | ✅✅ Médio |
| **Custo** | R$ 0 (imprimir) | R$ 0 (imprimir) |
| **Robustez** | ⚠️ Sensível à iluminação | ✅ Robusto |
| **Uso em campo** | ❌ Só para calibração | ✅ Calibração + medição em tempo real |
| **Recomendado para** | Calibração básica | Calibração precisa + sistema de medição |

**Quando usar Xadrez:**
- Primeira calibração (aprendizado)
- Ambiente controlado (boa iluminação)
- Precisão de ±5cm é aceitável

**Quando usar ArUco:**
- Precisão crítica (±1-3cm)
- Uso em campo (medição contínua)
- Iluminação variável
- Sistema profissional

---

### 8. Rotas da API de Calibração

```python
# Geração de PDFs
GET  /calibracao                  # Página de download
GET  /api/gerar_padrao_xadrez     # Baixa PDF xadrez
GET  /api/gerar_aruco_markers     # Baixa PDF ArUco

# Calibração em tempo real
GET  /calibracao_live             # Página de calibração
GET  /api/calibracao_stream       # Stream MJPEG com detecção
GET  /api/calibracao_status       # Status atual {pattern_detected, quality}
POST /api/calibracao_capturar     # Captura 1 foto
POST /api/calibracao_executar     # Executa calibração
POST /api/calibracao_resetar      # Limpa fotos capturadas

# Gestão de calibrações
GET  /api/calibracao_listar       # Lista calibrações salvas
POST /api/calibracao_deletar      # Deleta calibração
```

---

### 9. Fluxo Completo de Uso

```
┌─────────────────────────────────────────────┐
│ ETAPA 1: Preparação                         │
│ 1. Acessa /calibracao                       │
│ 2. Baixa PDF do padrão (xadrez ou ArUco)    │
│ 3. Imprime em A4 (100% de escala)           │
│ 4. Cola em superfície rígida e plana        │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ ETAPA 2: Captura de Fotos                   │
│ 1. Acessa /calibracao_live                  │
│ 2. Seleciona tipo de padrão                 │
│ 3. Segura padrão na frente da câmera        │
│ 4. Aguarda "Padrão detectado!" (luz verde)  │
│ 5. Clica "Capturar Frame" (foto 1)          │
│ 6. Muda ângulo/distância                    │
│ 7. Repete até 15-20 fotos                   │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ ETAPA 3: Calibração                         │
│ 1. Verifica: "12 fotos capturadas"          │
│ 2. Clica "Calibrar"                         │
│ 3. Aguarda processamento (~5-10s)           │
│ 4. Verifica erro < 1.0 px ✅               │
│ 5. Calibração salva em .npz                 │
└─────────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────────┐
│ ETAPA 4: Uso no Sistema                     │
│ 1. Sistema carrega calibracao_*.npz         │
│ 2. Corrige distorção de frames              │
│ 3. Mede buracos com precisão ±1-3cm         │
│ 4. Salva medidas no banco de dados          │
└─────────────────────────────────────────────┘
```

---

### 10. Resolução de Problemas

**Problema:** Padrão não é detectado (taxa 0%)

**Soluções:**
- ✅ Certifique que padrão está completamente visível
- ✅ Melhore iluminação (sem sombras)
- ✅ Aproxime o padrão da câmera
- ✅ Verifique se imprimiu na escala correta

---

**Problema:** Qualidade sempre baixa (< 40%)

**Soluções:**
- ✅ Limpe a lente da câmera
- ✅ Cole o padrão em superfície mais rígida
- ✅ Evite reflexos (flash, luz direta)
- ✅ Use padrão ArUco (mais robusto)

---

**Problema:** Erro de reprojeção alto (> 2.0 px)

**Soluções:**
- ✅ Tire mais fotos (20-25)
- ✅ Cubra mais ângulos diferentes
- ✅ Certifique que padrão está perfeitamente plano
- ✅ Verifique medida real do padrão impresso
- ✅ Resete e comece novamente

---

**Problema:** Botão "Calibrar" desabilitado

**Causa:** Menos de 10 fotos capturadas

**Solução:** Capture mais fotos até ter 10+

---

### 11. Atalhos no Sistema

**Na página inicial (`/`):**

```html
🗺️ [Mapa 2D]           → /map
📐 [Gerar Padrões]      → /calibracao
🎯 [Calibração Live]    → /calibracao_live
```

Todos abrem em nova aba para facilitar navegação.

---

### 12. Arquivos Criados

```
src/
├── pattern_generator.py          # Gera PDFs de calibração
├── api.py                         # +8 rotas de calibração
└── templates/
    ├── calibracao.html            # Download de PDFs
    └── calibracao_live.html       # Interface de calibração

deteccoes/
├── padrao_xadrez.pdf              # PDF gerado
└── aruco_markers.pdf              # PDF gerado

/
├── calibracao_chessboard.npz      # Calibração salva (xadrez)
└── calibracao_aruco.npz           # Calibração salva (ArUco)
```

---

### 13. Tecnologias Utilizadas

**Backend:**
- **ReportLab**: Geração de PDFs
- **OpenCV**: Detecção de padrões (cv2.findChessboardCorners, cv2.aruco)
- **NumPy**: Salvamento de calibrações (.npz)
- **Flask**: API REST

**Frontend:**
- **HTML5 + CSS3**: Interface responsiva
- **JavaScript (Vanilla)**: Interatividade
- **MJPEG Streaming**: Stream de vídeo em tempo real

**Algoritmos:**
- **cv2.calibrateCamera()**: Calibração com xadrez
- **cv2.aruco.calibrateCameraAruco()**: Calibração com ArUco
- **cv2.projectPoints()**: Cálculo de erro de reprojeção

---

### 14. Próximos Passos

**Integração futura:**
1. Carregar calibração automaticamente ao iniciar sistema
2. Botão "Aplicar calibração" no detector
3. Métricas de precisão em tempo real
4. Recalibração automática periódica
5. Detecção de ArUco em campo para medição contínua

---

**Versão:** 2.6 (Fase 6 - Sistema de Calibração Completo)  
**Última Atualização:** 06/Janeiro/2026  
**Autor:** Sistema Suple360 v2

