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
└── tracker.py         # 🎯 Rastreamento de buracos (FASE 1)
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
