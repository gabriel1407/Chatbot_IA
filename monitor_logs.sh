#!/bin/bash

# Script para monitorear logs del Chatbot IA
# Uso: ./monitor_logs.sh [tipo_log]
# Tipos: app, telegram, whatsapp, all

# Detectar la ubicación de los logs
if [ -f "openIAService/logs/app.log" ]; then
    LOG_DIR="openIAService/logs"
elif [ -f "openIAService/app.log" ]; then
    LOG_DIR="openIAService"
else
    LOG_DIR="openIAService/logs"  # Default para nuevos logs
fi

LOG_TYPE=${1:-"app"}

echo "🤖 MONITOR DE LOGS - CHATBOT IA"
echo "==============================="
echo "📍 Ubicación detectada: $LOG_DIR/"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

case $LOG_TYPE in
    "app")
        echo "📊 Monitoreando log principal: $LOG_DIR/app.log"
        echo "Presiona Ctrl+C para salir"
        echo ""
        if [ -f "$LOG_DIR/app.log" ]; then
            echo "=== ÚLTIMAS 10 LÍNEAS ==="
            tail -10 "$LOG_DIR/app.log"
            echo ""
            echo "=== SIGUIENDO EN TIEMPO REAL ==="
            tail -f "$LOG_DIR/app.log"
        else
            echo "⚠️ Archivo app.log no existe aún. Se creará cuando la aplicación se ejecute."
        fi
        ;;
    "telegram")
        echo "📱 Monitoreando log de Telegram: $LOG_DIR/telegram.log"
        echo "Presiona Ctrl+C para salir"
        echo ""
        if [ -f "$LOG_DIR/telegram.log" ]; then
            echo "=== ÚLTIMAS 10 LÍNEAS ==="
            tail -10 "$LOG_DIR/telegram.log"
            echo ""
            echo "=== SIGUIENDO EN TIEMPO REAL ==="
            tail -f "$LOG_DIR/telegram.log"
        else
            echo "⚠️ Archivo telegram.log no existe aún. Se creará cuando lleguen mensajes de Telegram."
        fi
        ;;
    "whatsapp")
        echo "💬 Monitoreando log de WhatsApp: $LOG_DIR/whatsapp.log"
        echo "Presiona Ctrl+C para salir"
        echo ""
        if [ -f "$LOG_DIR/whatsapp.log" ]; then
            echo "=== ÚLTIMAS 10 LÍNEAS ==="
            tail -10 "$LOG_DIR/whatsapp.log"
            echo ""
            echo "=== SIGUIENDO EN TIEMPO REAL ==="
            tail -f "$LOG_DIR/whatsapp.log"
        else
            echo "⚠️ Archivo whatsapp.log no existe aún. Se creará cuando lleguen mensajes de WhatsApp."
        fi
        ;;
    "all")
        echo "📊 Monitoreando TODOS los logs disponibles"
        echo "Presiona Ctrl+C para salir"
        echo ""
        # Verificar qué logs existen
        if [ -f "$LOG_DIR/app.log" ]; then
            echo "=== APP LOG (últimas 5 líneas) ==="
            tail -n 5 "$LOG_DIR/app.log"
            echo ""
        fi
        if [ -f "$LOG_DIR/telegram.log" ]; then
            echo "=== TELEGRAM LOG (últimas 5 líneas) ==="
            tail -n 5 "$LOG_DIR/telegram.log"
            echo ""
        fi
        if [ -f "$LOG_DIR/whatsapp.log" ]; then
            echo "=== WHATSAPP LOG (últimas 5 líneas) ==="
            tail -n 5 "$LOG_DIR/whatsapp.log"
            echo ""
        fi
        echo "=== SIGUIENDO TODOS LOS LOGS EN TIEMPO REAL ==="
        tail -f "$LOG_DIR"/*.log 2>/dev/null || echo "⚠️ No hay logs disponibles aún."
        ;;
    "status")
        echo "📊 ESTADO DE LOGS"
        echo ""
        for log_file in app.log telegram.log whatsapp.log; do
            if [ -f "$LOG_DIR/$log_file" ]; then
                size=$(du -h "$LOG_DIR/$log_file" | cut -f1)
                lines=$(wc -l < "$LOG_DIR/$log_file")
                last_modified=$(stat -c %y "$LOG_DIR/$log_file" | cut -d. -f1)
                echo "✅ $log_file: $size ($lines líneas) - Último: $last_modified"
            else
                echo "❌ $log_file: No existe"
            fi
        done
        echo ""
        echo "📍 Directorio de logs: $LOG_DIR/"
        
        # Mostrar últimas líneas de cada log
        echo ""
        echo "🔍 ÚLTIMAS ACTIVIDADES:"
        for log_file in app.log telegram.log whatsapp.log; do
            if [ -f "$LOG_DIR/$log_file" ]; then
                echo ""
                echo "--- $log_file (últimas 3 líneas) ---"
                tail -3 "$LOG_DIR/$log_file" | sed 's/^/  /'
            fi
        done
        ;;
    "errors")
        echo "🚨 BUSCANDO ERRORES EN LOGS"
        echo ""
        for log_file in "$LOG_DIR"/*.log; do
            if [ -f "$log_file" ]; then
                echo "=== ERRORES EN $(basename "$log_file") ==="
                grep -i -n "error\|exception\|traceback\|failed" "$log_file" | tail -10 || echo "  No se encontraron errores recientes"
                echo ""
            fi
        done
        ;;
    *)
        echo "❓ USO DEL SCRIPT:"
        echo ""
        echo "  $0 app       - Monitorea log principal de la aplicación"
        echo "  $0 telegram  - Monitorea log específico de Telegram"
        echo "  $0 whatsapp  - Monitorea log específico de WhatsApp"
        echo "  $0 all       - Monitorea todos los logs disponibles"
        echo "  $0 status    - Muestra estado de todos los logs"
        echo "  $0 errors    - Busca errores en todos los logs"
        echo ""
        echo "🔧 COMANDOS ÚTILES:"
        echo ""
        echo "  # Ver últimas 50 líneas del log principal"
        echo "  tail -50 $LOG_DIR/app.log"
        echo ""
        echo "  # Buscar errores en logs"
        echo "  grep -i error $LOG_DIR/*.log"
        echo ""
        echo "  # Ver logs de limpieza de contexto"
        echo "  grep -i cleanup $LOG_DIR/app.log"
        echo ""
        echo "  # Monitorear en tiempo real solo errores"
        echo "  tail -f $LOG_DIR/app.log | grep -i error"
        echo ""
        echo "  # Ver mensajes de WhatsApp recientes"
        echo "  grep -i whatsapp $LOG_DIR/app.log | tail -10"
        ;;
esac