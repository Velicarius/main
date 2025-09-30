# PowerShell скрипт для скачивания LLM моделей в Ollama
# Зачем: Автоматизирует загрузку моделей для тестирования разных LLM

Write-Host "🤖 Скачивание LLM моделей для AI Portfolio Analyzer..." -ForegroundColor Green

# Проверяем, что Ollama установлен и запущен
# Зачем: Без Ollama мы не сможем скачать модели
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Ollama не установлен! Сначала запустите: .\install.ps1" -ForegroundColor Red
    exit 1
}

# Проверяем, что сервер Ollama запущен
# Зачем: API сервер должен быть активен для скачивания
Write-Host "🔍 Проверяем, что Ollama сервер запущен..." -ForegroundColor Blue
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "✅ Ollama сервер работает на порту 11434" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama сервер не запущен!" -ForegroundColor Red
    Write-Host "💡 Запустите в отдельном терминале: ollama serve" -ForegroundColor Yellow
    Write-Host "   Затем запустите этот скрипт снова." -ForegroundColor Yellow
    exit 1
}

# Список моделей для скачивания
# Зачем: Определяем, какие модели нужны для разных задач анализа портфеля
$models = @(
    @{
        Name = "llama3.1:8b"
        Size = "4.1GB"
        Purpose = "Общий анализ портфеля, финансовые рассуждения"
        Quantized = "q4_0"  # 4-битная квантизация для экономии места
    },
    @{
        Name = "gemma2:9b"
        Size = "5.4GB" 
        Purpose = "Быстрые ответы, код-генерация"
        Quantized = "q4_0"  # Оптимизирована Google для скорости
    },
    @{
        Name = "qwen2.5-coder:7b"
        Size = "4.4GB"
        Purpose = "Генерация SQL/Python кода для анализа данных"
        Quantized = "q4_0"  # Специализирована на коде
    }
)

Write-Host "📋 Планируется скачать ${models.Count} моделей:" -ForegroundColor Cyan
foreach ($model in $models) {
    Write-Host "  • $($model.Name) ($($model.Size)) - $($model.Purpose)" -ForegroundColor Gray
}

Write-Host ""
$confirm = Read-Host "Продолжить? (y/N)"
if ($confirm -ne "y" -and $confirm -ne "Y") {
    Write-Host "❌ Отменено пользователем" -ForegroundColor Yellow
    exit 0
}

# Функция для скачивания модели с прогресс-баром
# Зачем: Показываем прогресс, так как модели большие (4-5GB)
function Download-Model {
    param($modelName, $description)
    
    Write-Host "📥 Скачиваем $modelName..." -ForegroundColor Blue
    Write-Host "   Назначение: $description" -ForegroundColor Gray
    
    try {
        # Запускаем ollama pull в фоне для отслеживания прогресса
        # Зачем: ollama pull не показывает прогресс, поэтому запускаем с выводом
        $process = Start-Process -FilePath "ollama" -ArgumentList "pull", $modelName -PassThru -NoNewWindow -RedirectStandardOutput -RedirectStandardError
        
        # Ждем завершения с таймаутом
        # Зачем: Предотвращаем зависание скрипта
        $timeout = 1800  # 30 минут на модель
        if ($process.WaitForExit($timeout * 1000)) {
            if ($process.ExitCode -eq 0) {
                Write-Host "✅ $modelName успешно скачан!" -ForegroundColor Green
                return $true
            } else {
                Write-Host "❌ Ошибка скачивания $modelName (код: $($process.ExitCode))" -ForegroundColor Red
                return $false
            }
        } else {
            Write-Host "⏰ Таймаут скачивания $modelName" -ForegroundColor Yellow
            $process.Kill()
            return $false
        }
    } catch {
        Write-Host "❌ Исключение при скачивании $modelName : $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Скачиваем каждую модель
# Зачем: Последовательно скачиваем модели, чтобы не перегружать систему
$successCount = 0
$totalSize = 0

foreach ($model in $models) {
    Write-Host ""
    Write-Host "🔄 Обрабатываем $($model.Name)..." -ForegroundColor Cyan
    
    # Проверяем, не скачана ли уже модель
    # Зачем: Избегаем повторного скачивания
    try {
        $existingModels = ollama list | Out-String
        if ($existingModels -match $model.Name) {
            Write-Host "✅ $($model.Name) уже установлен, пропускаем" -ForegroundColor Yellow
            $successCount++
            continue
        }
    } catch {
        # Игнорируем ошибки проверки, продолжаем скачивание
    }
    
    if (Download-Model -modelName $model.Name -description $model.Purpose) {
        $successCount++
        # Парсим размер для подсчета общего размера
        if ($model.Size -match "(\d+\.?\d*)GB") {
            $totalSize += [double]$matches[1]
        }
    }
    
    # Небольшая пауза между скачиваниями
    # Зачем: Даем системе время на обработку
    Start-Sleep -Seconds 2
}

# Итоговый отчет
# Зачем: Показываем результат работы скрипта
Write-Host ""
Write-Host "📊 Результат скачивания:" -ForegroundColor Cyan
Write-Host "  ✅ Успешно: $successCount из $($models.Count)" -ForegroundColor Green
Write-Host "  💾 Общий размер: ~${totalSize}GB" -ForegroundColor Blue

if ($successCount -eq $models.Count) {
    Write-Host "🎉 Все модели успешно скачаны!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Следующие шаги:" -ForegroundColor Cyan
    Write-Host "1. Убедитесь, что Ollama сервер запущен: ollama serve" -ForegroundColor White
    Write-Host "2. Тестируйте модели: http://localhost:8000/llm_test.html" -ForegroundColor White
    Write-Host "3. Проверьте список: ollama list" -ForegroundColor White
} else {
    Write-Host "⚠️  Некоторые модели не скачались. Проверьте подключение к интернету." -ForegroundColor Yellow
    Write-Host "💡 Попробуйте скачать вручную: ollama pull <model_name>" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "💡 Полезные команды:" -ForegroundColor Yellow
Write-Host "   ollama list                    - список моделей" -ForegroundColor Gray
Write-Host "   ollama run llama3.1:8b         - интерактивный режим" -ForegroundColor Gray
Write-Host "   ollama rm <model>              - удалить модель" -ForegroundColor Gray
Write-Host "   ollama serve                   - запустить API сервер" -ForegroundColor Gray

