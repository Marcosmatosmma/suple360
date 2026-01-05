📁 ESTRUTURA DE ARQUIVOS ESTÁTICOS
==================================

A aplicação agora usa arquivos locais em vez de CDN, permitindo funcionar SEM internet.

📂 /src/static/
├── css/
│   └── style.css         (6.9 KB) - CSS framework leve e responsivo
└── js/
    └── vue.global.js     (562 KB) - Vue.js 3 para frontend interativo

🔧 CONFIGURAÇÃO
===============

O Flask foi configurado para servir arquivos estáticos:
- static_folder='static'
- static_url_path='/static'

No HTML:
- <link rel="stylesheet" href="/static/css/style.css">
- <script src="/static/js/vue.global.js"></script>

✅ RECURSOS DO CSS
==================

Framework leve similar ao Bootstrap com:
- ✓ Grid responsivo (1 a 2 colunas)
- ✓ Cards com hover effects
- ✓ Botões com gradientes
- ✓ Indicador de status com animação
- ✓ Status bar translúcida
- ✓ Badges e alerts
- ✓ Media queries para mobile
- ✓ Variáveis CSS para fácil customização
- ✓ Apenas 6.9 KB (muito leve!)

🎨 PALETA DE CORES
==================

--primary: #667eea (Roxo principal)
--primary-dark: #764ba2 (Roxo escuro)
--success: #4CAF50 (Verde)
--danger: #f44336 (Vermelho)
--warning: #ff9800 (Laranja)
--info: #2196F3 (Azul)

📱 RESPONSIVO
=============

- Desktop (1000px): Layout 2 colunas
- Tablet (768px): Grid auto-fit
- Mobile (480px): Layout 1 coluna, botões full-width

🚀 COMO USAR
============

1. Execute normalmente:
   ./run.sh

2. Acesse em:
   http://192.168.101.16:5000

3. Funciona SEM internet - todos os arquivos estão locais!

💡 BENEFÍCIOS
=============

✓ Funciona offline (sem CDN)
✓ Carregamento mais rápido
✓ Menor consumo de banda
✓ CSS e JS levíssimos (567 KB total)
✓ Design moderno e responsivo
✓ Compatível com Vue.js 3

⚡ PERFORMANCE
===============

Tamanho total dos assets:
- vue.global.js: 562 KB
- style.css: 6.9 KB
- Total: ~569 KB

Sem dependências externas após download inicial!
