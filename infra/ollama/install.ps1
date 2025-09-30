# PowerShell скрипт для установки Ollama на Windows
# Зачем: Автоматизирует установку Ollama для локального запуска LLM

Write-Host "🚀 Установка Ollama для AI Portfolio Analyzer..." -ForegroundColor Green

# Проверяем, установлен ли уже Ollama
# Зачем: Избегаем повторной установки
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "✅ Ollama уже установлен!" -ForegroundColor Yellow
    ollama --version
    Write-Host "💡 Для обновления: winget upgrade Ollama.Ollama" -ForegroundColor Cyan
    exit 0
}

Write-Host "📦 Устанавливаем Ollama через winget..." -ForegroundColor Blue

# Устанавливаем Ollama через Windows Package Manager
# Зачем: winget - официальный пакетный менеджер Windows, безопаснее чем скачивать .exe
try {
    winget install Ollama.Ollama --accept-package-agreements --accept-source-agreements
    Write-Host "✅ Ollama успешно установлен!" -ForegroundColor Green
} catch {
    Write-Host "❌ Ошибка установки через winget. Пробуем альтернативный способ..." -ForegroundColor Red
    
    # Альтернативный способ: скачивание с официального сайта
    # Зачем: Если winget не работает, используем прямой скачивание
    $downloadUrl = "https://ollama.ai/download/windows"
    Write-Host "🌐 Открываем страницу скачивания: $downloadUrl" -ForegroundColor Cyan
    Start-Process $downloadUrl
    
    Write-Host "📥 Скачайте и установите Ollama вручную, затем запустите этот скрипт снова." -ForegroundColor Yellow
    exit 1
}

# Проверяем установку
# Зачем: Убеждаемся, что Ollama работает корректно
Write-Host "🔍 Проверяем установку..." -ForegroundColor Blue
try {
    $version = ollama --version
    Write-Host "✅ Версия Ollama: $version" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama установлен, но не работает. Попробуйте перезагрузить терминал." -ForegroundColor Red
    exit 1
}

# Создаем папку для моделей (если нужно)
# Зачем: Предварительная подготовка для скачивания моделей
$modelsPath = "$env:USERPROFILE\.ollama\models"
if (-not (Test-Path $modelsPath)) {
    New-Item -ItemType Directory -Path $modelsPath -Force | Out-Null
    Write-Host "📁 Создана папка для моделей: $modelsPath" -ForegroundColor Green
}

Write-Host "🎉 Установка завершена!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
Write-Host "1. Запустите сервер: ollama serve" -ForegroundColor White
Write-Host "2. Скачайте модели: .\pull_models.ps1" -ForegroundColor White
Write-Host "3. Тестируйте: http://localhost:8000/llm_test.html" -ForegroundColor White
Write-Host ""
Write-Host "💡 Полезные команды:" -ForegroundColor Yellow
Write-Host "   ollama list          - список установленных моделей" -ForegroundColor Gray
Write-Host "   ollama pull model    - скачать модель" -ForegroundColor Gray
Write-Host "   ollama run model     - запустить модель в интерактивном режиме" -ForegroundColor Gray

