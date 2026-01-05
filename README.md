# Suple 360 - Sistema de Detecção de Buracos em Tempo Real

## 📋 Sobre o Projeto

**Suple 360** é um sistema inteligente de detecção de buracos (panelas) em estradas utilizando visão computacional e LIDAR. O projeto combina **hardware embarcado** (Raspberry Pi 5), **inteligência artificial** (YOLOv8 customizado), **sensoriamento 360°** (RPLIDAR A1M8) e uma **interface web interativa** para visualizar detecções em tempo real.

### Objetivo Principal
Automatizar a identificação de defeitos em pavimentos, fornecendo dados geoespaciais precisos (localização, dimensões, confiança) através de uma plataforma web responsiva e fácil de usar.

---

## 🛠️ Stack Tecnológico

### Hardware
- **Processador**: Raspberry Pi 5 (8GB RAM)
- **Câmera**: IMX477 (1280x720 @ 30fps, formato XBGR8888)
- **LIDAR**: RPLIDAR A1M8 (comunicação via /dev/ttyUSB0 @ 115200 baud)
- **Armazenamento**: SSD local para modelos e imagens de detecção

### Inteligência Artificial
- **Framework**: YOLOv8 (Ultralytics)
- **Modelo**: Custom treinado para detecção de buracos (`model/best.pt`)
- **Processamento**: 640x360 downscale em tempo real (~2-3s por frame)

### Backend
- **Framework**: Flask (Python 3.13)
- **Servidor**: 0.0.0.0:5000
- **Banco de Dados**: SQLite3 (`detections.db`)
- **Templates**: Jinja2 com suporte a Vue.js 3

### Frontend
- **Framework**: Vue.js 3 (build local 562KB)
- **Estilo**: CSS customizado com tema escuro
- **Responsividade**: Mobile-first, compatível com desktop

### Comunicação
- **Protocolo**: RESTful JSON API
- **Polling em Tempo Real**: 
  - Detecções: 2 segundos
  - LIDAR: 500ms

---

## ✨ Funcionalidades Implementadas

### 1. **Detecção de Buracos em Tempo Real**
- ✅ Captura contínua de vídeo da câmera IMX477
- ✅ Processamento com YOLOv8 customizado
- ✅ Armazenamento de imagens de detecção (JPG)
- ✅ Registro de metadados: timestamp, contagem de buracos, caminhos de arquivos

### 2. **Mapeamento LIDAR 360°**
- ✅ Leitura contínua do RPLIDAR A1M8
- ✅ Agregação de dados em setores de 5°
- ✅ Rendering em canvas 2D com grid de escala
- ✅ **Controle dinâmico de escala** (0.5m a 10m ajustável)
- ✅ Detecção automática de status online/offline
- ✅ Auto-reconexão com fallback em caso de erro

### 3. **Dashboard Web Interativo**
- ✅ Visualização ao vivo do vídeo da câmera
- ✅ Mapa LIDAR em tempo real no mesmo painel
- ✅ Tabela de histórico de detecções com buracos por imagem
- ✅ **Página dedicada fullscreen** (/lidar) com mapa LIDAR expandido
- ✅ Indicadores de status (câmera online, LIDAR online, timestamps)
- ✅ Botões funcionais: "Test LIDAR", "Clear History", "Open LIDAR"

### 4. **Persistência de Dados**
- ✅ Banco de dados SQLite com 2 tabelas:
  - **detections**: id, timestamp, photo_path, num_buracos, created_at
  - **buracos**: id, detection_id, bbox (x1/y1/x2/y2), confiança, distância, largura
- ✅ API de consulta: últimas detecções, estatísticas gerais
- ✅ Limpeza completa com recriação de schema
- ✅ **Endpoint `/api/db-info`** para monitorar contagem de registros

### 5. **API RESTful Completa**
- `GET /` - Dashboard principal
- `GET /lidar` - Página fullscreen LIDAR
- `GET /api/lidar/latest` - Últimos dados LIDAR em JSON
- `GET /api/detections/recent` - Últimas 20 detecções com buracos
- `GET /api/detections/stats` - Estatísticas gerais
- `GET /api/detections/<id>` - Detecção específica
- `GET /api/test-lidar` - Teste de distâncias por setor
- `GET /api/db-info` - Informações do banco (contagem, tamanho)
- `POST /api/clear-history` - Limpa histórico completo
- `GET /deteccoes/<filename>` - Serve imagens detectadas

### 6. **Tratamento de Erros e Robustez**
- ✅ Fallback LIDAR: `iter_scans()` quando `iter_measurements()` falha
- ✅ Auto-reconexão LIDAR com loop `while True`
- ✅ Threads seguras com locks (`threading.Lock`)
- ✅ Logging estruturado de operações
- ✅ Tratamento de exceções em endpoints críticos

### 7. **Interface de Usuário Polida**
- ✅ Layout responsivo: 70% câmera, 30% LIDAR em desktop
- ✅ CSS otimizado: objeto-fit contain, sem cortes de imagem
- ✅ Tema escuro profissional (#0a0a0a, #667eea, #2a2a2a)
- ✅ Controle de escala LIDAR com slider intuitivo
- ✅ Grid de histórico com formatação de datas
- ✅ Resolução de conflito Jinja2/Vue.js com tags `{% raw %}`

---

## 📁 Estrutura do Projeto

```
/home/suple/Desktop/suple360v2/
├── src/
│   ├── main.py                    # Aplicação Flask + threads de processamento
│   ├── templates/
│   │   ├── index.html            # Dashboard principal (Vue.js)
│   │   ├── lidar.html            # Página fullscreen LIDAR (Vue.js)
│   │   └── base.html             # Template base
│   ├── static/
│   │   └── style.css             # Estilos CSS customizados
│   └── vue.js                     # Build local Vue.js 3
├── model/
│   └── best.pt                    # Modelo YOLOv8 customizado treinado
├── deteccoes/                     # Diretório de armazenamento
│   ├── detections.db             # Banco de dados SQLite
│   └── *.jpg                      # Imagens de detecções
├── run.sh                         # Script de inicialização
└── README.md                      # Este arquivo

```

---

## 🚀 Como Usar

### 1. **Iniciar a Aplicação**

```bash
cd /home/suple/Desktop/suple360v2
chmod +x run.sh
./run.sh
```

A aplicação iniciará em `http://localhost:5000`

### 2. **Acessar o Dashboard**

- **Dashboard Principal**: http://localhost:5000/
  - Vídeo ao vivo + Mapa LIDAR + Histórico de detecções
  
- **Página Fullscreen LIDAR**: http://localhost:5000/lidar
  - Mapa LIDAR expandido com controle de escala

### 3. **Monitorar Banco de Dados**

```bash
# Ver contagem de registros
curl http://localhost:5000/api/db-info | python3 -m json.tool
```

Resposta esperada:
```json
{
    "db_exists": true,
    "db_size_bytes": 16384,
    "total_detections": 4,
    "total_potholes": 0
}
```

### 4. **Controles da Interface**

- 🎚️ **Scale Slider**: Ajuste o alcance do LIDAR (0.5m - 10m)
- 🧪 **Test LIDAR**: Teste conexão e veja distâncias por setor
- 🗑️ **Clear History**: Limpe todas as detecções e imagens
- 📱 **Open LIDAR**: Abre mapa LIDAR em nova aba fullscreen

---

## 🔧 Componentes Principais

### main.py (554 linhas)

#### DatabaseManager
Gerencia todas as operações SQLite com segurança de threads:
- `_init_db()` - Cria schema com 2 tabelas
- `add_detection()` - Insere detecção + buracos em transação
- `get_recent()` - Retorna últimas detecções com buracos relacionados
- `get_stats()` - Calcula estatísticas gerais

#### Threads de Processamento
1. **Flask** - Servidor web principal
2. **Camera** - Captura contínua frames (1280x720)
3. **YOLO** - Inferência de detecção em frames
4. **LIDAR** - Leitura contínua do sensor (iter_scans com 5° agregação)

#### Endpoints Críticos
- `/api/detections/recent` - Query ao banco com left join
- `/api/clear-history` - Delete DB + Remove JPGs + Reinit schema
- `/api/db-info` - Conta registros sem aceitar parâmetros (novo)
- `/api/lidar/latest` - Retorna últimos dados LIDAR no formato setor→medições

### index.html (Vue.js)

**Seções principais:**
- 📹 **Video Stream** (70% width)
- 🗺️ **LIDAR Map** com canvas (30% width)
- ⏱️ **Detection History** - Grid de detecções
- 🎚️ **Scale Control** - Slider 0.5m-10m
- 🔘 **Action Buttons** - Test, Clear, Open LIDAR

**Métodos Vue:**
- `drawLidarMap()` - Renderiza canvas com pontos LIDAR + grid
- `updateLidar()` - Polling de `/api/lidar/latest`
- `loadDetections()` - Polling de `/api/detections/recent`
- `clearHistory()` - POST para `/api/clear-history` com confirmação
- `testLidar()` - GET `/api/test-lidar` mostra distâncias por setor

### lidar.html (Página Fullscreen)

**Características especiais:**
- Canvas 1000x1000px (maior que index.html)
- Scale control com display dinâmico
- Mesma lógica de renderização que index.html
- Tags `{% raw %}...{% endraw %}` para evitar conflito Jinja2/Vue
- Polling independente a cada 500ms

### style.css

**Componentes principais:**
- `.lidar-scale-control` - Flex layout, 140px width
- `.lidar-scale-control input[type="range"]` - Estilo customizado
- `.lidar-scale-display` - Badge mostrando valor em metros
- Tema escuro consistente (#0a0a0a background, #667eea accent)

---

## 🐛 Problemas Resolvidos

| Problema | Solução |
|----------|---------|
| RPLIDAR offline no boot | Removido `start_motor()`, usado `iter_scans()` com auto-reconnect |
| Vídeo cortado verticalmente | Mudado CSS para `object-fit: contain` com `height: auto` |
| "Too many values to unpack" do LIDAR | Implementado fallback: `iter_scans()` ao invés de `iter_measurements()` |
| Template Jinja2/Vue.js conflito | Envolvido Vue content em `{% raw %}...{% endraw %}` |
| Escala LIDAR hardcoded | Adicionado slider dinâmico (0.5m-10m) com v-model binding |
| Clear History não reflete no DB | Adicionado endpoint `/api/db-info` para monitoramento |

---

## 📊 Especificações Técnicas

### Performance
- **FPS Câmera**: 30fps (1280x720)
- **Latência YOLO**: 2-3 segundos por frame
- **Taxa Polling LIDAR**: 500ms (2 atualizações/segundo)
- **Taxa Polling Detecções**: 2 segundos
- **Pontos LIDAR por Setor**: ~40-100 após agregação 5°

### Consumo de Recursos (Raspberry Pi 5)
- **Threads**: 4 daemons + 1 principal
- **Memória BD**: ~16KB para schema vazio
- **Tipo de Lock**: `threading.Lock` para thread-safety SQLite
- **Timeout Conexão**: Sem timeout especificado (bloqueante)

### Conformidade
- ✅ Python 3.13
- ✅ Flask 2.x
- ✅ Vue.js 3.x
- ✅ SQLite3 (built-in Python)
- ✅ YOLOv8 (Ultralytics)
- ✅ OpenCV (cv2)
- ✅ RPLidar (pip library)

---

## 📝 Próximos Passos (Futuro)

- [ ] Geolocalização com GPS para registrar coordenadas
- [ ] Exportação de dados (CSV, GeoJSON)
- [ ] Relatórios em PDF com mapas
- [ ] Integração com mapas (Folium, Leaflet)
- [ ] Autenticação de usuários
- [ ] Dashboard Admin para gerenciar múltiplos equipamentos
- [ ] Alertas em tempo real via webhook
- [ ] Compressão de vídeo H.264 para arquivo

---

## 👨‍💻 Autor

Desenvolvido por **Suple** - Sistema de Inteligência para Infraestrutura Viária

**Versão**: 2.0  
**Data**: Janeiro 2026  
**Status**: Produção

---

## 📄 Licença

Propriedade privada - Todos os direitos reservados

---

## 🙋 Suporte

Para problemas ou dúvidas, consulte os logs em `/tmp/suple360.log`

```bash
tail -f /tmp/suple360.log
```

