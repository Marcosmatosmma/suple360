#!/bin/bash
# Script para rodar a detecção de buracos
# Sempre usa o Python do sistema (/usr/bin/python3) para ter acesso a libcamera

# Desativa venv se estiver ativo
if [ -n "$VIRTUAL_ENV" ]; then
    echo "❌ Venv ativo detectado. Desativando..."
    deactivate 2>/dev/null || true
fi

# Muda para o diretório src
cd "$(dirname "$0")/src" || exit 1

# Executa com Python do sistema (não do venv)
echo "🚀 Iniciando Sistema de Detecção de Buracos..."
/usr/bin/python3 main.py
