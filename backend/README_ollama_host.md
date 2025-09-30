# Диагностика подключения к Ollama из Docker

## Проблема
API в Docker контейнере не может подключиться к Ollama, запущенному на Windows-хосте.

## Диагностика

### 1. Проверка Ollama на хосте
```bash
# Проверяем, что Ollama запущен и отвечает
curl http://127.0.0.1:11434/api/version
```

Ожидаемый ответ:
```json
{"version":"0.1.0"}
```

### 2. Проверка из Docker контейнера
```bash
# Проверяем диагностический endpoint
curl http://localhost:8001/debug/connect
```

Ожидаемый ответ:
```json
{
  "ollama_url": "http://host.docker.internal:11434",
  "dns": {
    "host": "host.docker.internal",
    "ip": "192.168.1.100"
  },
  "tcp_ok": true,
  "http_ok": true,
  "error": null
}
```

## Решение проблем

### Если `tcp_ok=false` → проблема с firewall

**Windows Firewall блокирует подключения к порту 11434**

Решение (PowerShell от имени администратора):
```powershell
# Разрешаем входящие подключения к порту 11434
New-NetFirewallRule -DisplayName "Ollama 11434" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 11434

# Проверяем, что правило создано
Get-NetFirewallRule -DisplayName "Ollama 11434"
```

### Если `http_ok=false`, но `tcp_ok=true` → проблема с привязкой Ollama

**Ollama слушает только на localhost, а не на всех интерфейсах**

Решение:
```bash
# Останавливаем Ollama
# Затем запускаем с привязкой ко всем интерфейсам
$env:OLLAMA_HOST="0.0.0.0:11434"
ollama serve
```

### Если `dns.ip` пустой → проблема с DNS

**host.docker.internal не резолвится**

Решение:
1. Проверьте, что в `docker-compose.yml` есть:
   ```yaml
   extra_hosts:
     - "host.docker.internal:host-gateway"
   ```

2. Перезапустите контейнеры:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Альтернативные решения

### Вариант 1: Использование IP адреса хоста
```yaml
# В docker-compose.yml
environment:
  OLLAMA_URL: "http://192.168.1.100:11434"  # Замените на ваш IP
```

### Вариант 2: Проброс порта Ollama
```yaml
# В docker-compose.yml
ports:
  - "11435:11434"  # Пробрасываем порт Ollama
environment:
  OLLAMA_URL: "http://localhost:11435"
```

### Вариант 3: Запуск Ollama в Docker
```yaml
# Добавить в docker-compose.yml
ollama:
  image: ollama/ollama:latest
  container_name: infra-ollama-1
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  environment:
    - OLLAMA_HOST=0.0.0.0:11434

volumes:
  ollama_data:
```

## Проверка после исправления

1. Перезапустите контейнеры:
   ```bash
   docker-compose restart api
   ```

2. Проверьте диагностику:
   ```bash
   curl http://localhost:8001/debug/connect
   ```

3. Проверьте LLM endpoint:
   ```bash
   curl http://localhost:8001/llm/health
   ```

## Логи для отладки

```bash
# Логи API контейнера
docker-compose logs api

# Логи с фильтром по Ollama
docker-compose logs api | grep -i ollama
```
