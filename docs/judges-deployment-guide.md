# 🧭 AI Tourist — Judge Deployment Runbook

Этот документ — максимально подробный план, который позволит запустить проект даже человеку без опыта в Docker/Kubernetes. Читайте разделы по порядку и выполняйте шаги один за другим. Никаких дополнительных секретов или ручных настроек не требуется — всё уже лежит в архиве.

---

## 🔖 Легенда

| Символ | Значение |
|:------:|----------|
| ✅ | Всё хорошо, переходите дальше |
| ⚠️ | Предупреждение. Можно продолжать, но лучше выполнить рекомендацию |
| ❌ | Критичная проблема. Остановитесь, исправьте ошибку и повторите шаг |
| 💡 | Полезные подсказки и дополнительная информация |
| 🔧 | Технические детали и настройки |
| 🚀 | Готово к запуску |

---

## 0. Предварительная подготовка (один раз на ноутбуке)

### 0.1 Выберите, откуда запускать команды

Выбор правильной оболочки критически важен для успешного выполнения команд:

| Операционная система | Рекомендуемая оболочка | Примечания |
|---------------------|------------------------|------------|
| **macOS** | Встроенный Terminal или iTerm2 | Поддержка всех Bash-скриптов из коробки |
| **Windows 10/11** | **PowerShell 5.x+** (любая версия) | Запускайте «Run as Administrator» для установки зависимостей |
| **Windows с WSL2** | Терминал Ubuntu/Debian внутри WSL2 | Полная Linux-совместимость, рекомендуется для опытных пользователей |
| **Linux (Ubuntu/Debian)** | Любой терминал Bash | Нативная поддержка всех команд |

#### 🪟 Важно для пользователей Windows

**Разница между версиями PowerShell:**
- **PowerShell 5.x** — встроен в Windows 10/11 (команда: `powershell`)
- **PowerShell 7+** — современная версия (команда: `pwsh`, требует установки)

> 🔧 **Проверьте версию PowerShell:**
> ```powershell
> $PSVersionTable.PSVersion
> ```

**Если у вас PowerShell 5.x:**
- Команды в документе используют `pwsh`, замените на `powershell`
- Или установите PowerShell 7+ (рекомендуется): `winget install Microsoft.PowerShell`

---

#### 🚨 Решение проблемы "Выполнение сценариев отключено" (Execution Policy)

Если при запуске `.ps1` файлов вы видите ошибку:
```
Невозможно загрузить файл, так как выполнение сценариев отключено в этой системе
PSSecurityException
UnauthorizedAccess
```

Это означает, что Windows блокирует выполнение скриптов из соображений безопасности.

##### ✅ Решение 1: Разрешить на время (РЕКОМЕНДУЕТСЯ)

Самый безопасный способ — разрешить только для текущей сессии PowerShell:

```powershell
# Откройте PowerShell (НЕ обязательно от администратора)
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Теперь запустите скрипт
cd C:\Users\Ya\Desktop\gorkycode
.\scripts\judge-run.ps1
```

> 💡 Это разрешение действует только пока открыто окно PowerShell. После закрытия всё вернётся к безопасным настройкам.

##### ✅ Решение 2: Разрешить для текущего пользователя

Более удобно, но менее безопасно:

```powershell
# Откройте PowerShell от администратора (ПКМ → "Запуск от имени администратора")
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Подтвердите изменение (введите Y)
# Теперь закройте и откройте PowerShell снова (уже можно без прав админа)

# Запустите скрипт
cd C:\Users\Ya\Desktop\gorkycode
.\scripts\judge-run.ps1
```

> ⚠️ Это изменение постоянное для вашего пользователя, но не влияет на других пользователей системы.

##### ✅ Решение 3: Bypass для одной команды

Запустить скрипт с временным обходом политики:

```powershell
# Не нужны права администратора
powershell -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1

# Или для PowerShell 7+:
pwsh -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1
```

##### ✅ Решение 4: Без прав администратора

Если у вас НЕТ прав администратора, используйте:

```powershell
# Способ 1: Через параметр команды
powershell -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1

# Способ 2: Unblock конкретного файла
Unblock-File -Path .\scripts\judge-run.ps1
.\scripts\judge-run.ps1

# Способ 3: Через Get-Content
Get-Content .\scripts\judge-run.ps1 | powershell -NoProfile -
```

##### 📋 Проверка текущей политики

Узнайте, какая политика сейчас установлена:

```powershell
Get-ExecutionPolicy -List
```

**Возможные значения:**
- `Restricted` — скрипты запрещены (по умолчанию на Windows)
- `RemoteSigned` — локальные скрипты разрешены, скачанные требуют подписи
- `Unrestricted` — все скрипты разрешены (небезопасно)
- `Bypass` — все скрипты разрешены, предупреждения отключены

##### 🎯 Наша рекомендация

Для работы с проектом используйте **Решение 1** (Bypass для процесса):

```powershell
# 1. Откройте PowerShell
# 2. Выполните:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# 3. Перейдите в папку проекта:
cd C:\Users\Ya\Desktop\gorkycode

# 4. Запустите скрипт:
.\scripts\judge-run.ps1
```

Это безопасно и не требует прав администратора! ✅

---

### 0.2 Установите требуемые инструменты

Установка разделена по категориям для удобства:

#### 🖥️ Виртуализация и гипервизоры

| ОС | Требования | Команды/Действия |
|----|-----------|------------------|
| **macOS** | Включено по умолчанию | Проверка: `sysctl kern.hv_support` → должно вернуть `1` |
| **Windows 10/11** | Intel VT-x / AMD-V в BIOS | Включите в BIOS/UEFI. Если Hyper-V недоступен (Windows Home), включите виртуализацию для VirtualBox |
| **Linux** | Intel VT-x / AMD-V в BIOS | Включите в BIOS/UEFI |

> ⚠️ **Без виртуализации** Minikube не запустится. Обязательно проверьте этот параметр перед продолжением.

#### ☸️ Kubernetes инструменты

**Minikube**
- **macOS**: `brew install minikube`
- **Windows**: `winget install Kubernetes.minikube`
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt-get update && sudo apt-get install -y curl conntrack
  curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
  sudo install minikube /usr/local/bin/
  ```

> 💡 После установки проверьте версию: `minikube version`

**kubectl**
- **macOS**: `brew install kubectl`
- **Windows**: `winget install Kubernetes.kubectl`
- **Linux**: `sudo apt-get install -y kubectl`

> 💡 Проверьте установку: `kubectl version --client`

**Helm**
- **macOS**: `brew install helm`
- **Windows**: `winget install Kubernetes.Helm`
- **Linux**: `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash`

> 💡 Проверьте установку: `helm version`

#### 🐳 Контейнеризация (опционально)

**Docker Desktop**

| ОС | Установка | Альтернатива |
|----|-----------|--------------|
| **macOS** | [docker.com](https://www.docker.com/products/docker-desktop/) | VirtualBox + `--driver=virtualbox` |
| **Windows** | [docker.com](https://www.docker.com/products/docker-desktop/) | VirtualBox + `--driver=virtualbox` |
| **Linux** | `sudo apt-get install -y docker.io` | Используйте `minikube image build` без Docker |

> ⚠️ **Если нельзя установить Docker Desktop** — это нормально. Скрипты автоматически переключаются на `minikube image build`. Достаточно иметь Minikube + VirtualBox/Podman.

**VirtualBox** *(если работаете без Docker)*

| ОС | Установка |
|----|-----------|
| **macOS** | `brew install --cask virtualbox` (потребуется перезагрузка) |
| **Windows** | [virtualbox.org](https://www.virtualbox.org/wiki/Downloads) |
| **Linux** | `sudo apt-get install -y virtualbox` |

#### 🛠️ Утилиты разработки

**Make** *(опционально, но рекомендуется)*

| ОС | Установка |
|----|-----------|
| **macOS** | Входит в Xcode CLT: `xcode-select --install` |
| **Windows** | `winget install GnuWin32.Make` или `choco install make`<br>Скрипт автоматически добавит `C:\Program Files (x86)\GnuWin32\bin` в PATH |
| **Linux** | `sudo apt-get install -y make` |

> 💡 Проверьте установку: `make --version`

#### 🔧 Если `make --version` не работает после установки

Это означает, что путь к Make не добавлен в PATH. Выполните следующие шаги для вашей ОС:

**macOS:**

1. **Проверьте, где установлен make:**
   ```bash
   which make
   # Обычно: /usr/bin/make или /Library/Developer/CommandLineTools/usr/bin/make
   ```

2. **Если команда не найдена, установите Xcode Command Line Tools:**
   ```bash
   xcode-select --install
   ```

3. **Добавьте в PATH (если нужно):**
   ```bash
   # Откройте файл конфигурации
   nano ~/.zshrc  # для zsh (по умолчанию в macOS)
   # или
   nano ~/.bash_profile  # для bash
   
   # Добавьте строку:
   export PATH="/Library/Developer/CommandLineTools/usr/bin:$PATH"
   
   # Сохраните (Ctrl+O, Enter, Ctrl+X)
   
   # Перезагрузите конфигурацию
   source ~/.zshrc  # или source ~/.bash_profile
   ```

4. **Проверьте снова:**
   ```bash
   make --version
   ```

**Windows (PowerShell):**

1. **Найдите путь установки Make:**
   ```powershell
   # GnuWin32 обычно устанавливается в:
   # C:\Program Files (x86)\GnuWin32\bin
   
   # Chocolatey обычно устанавливается в:
   # C:\ProgramData\chocolatey\bin
   
   # Проверьте наличие файла
   Test-Path "C:\Program Files (x86)\GnuWin32\bin\make.exe"
   ```

2. **Добавьте в PATH (временно для текущей сессии):**
   ```powershell
   $env:PATH += ";C:\Program Files (x86)\GnuWin32\bin"
   
   # Проверьте
   make --version
   ```

3. **Добавьте в PATH (постоянно):**
   
   **Вариант A: Через PowerShell (от администратора):**
   ```powershell
   # Получите текущий PATH
   $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
   
   # Добавьте новый путь
   $newPath = $currentPath + ";C:\Program Files (x86)\GnuWin32\bin"
   
   # Установите обновлённый PATH
   [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
   
   # Перезапустите PowerShell для применения изменений
   ```

   **Вариант B: Через GUI:**
   - Нажмите `Win + X` → **System** (Система)
   - Нажмите **Advanced system settings** (Дополнительные параметры системы)
   - Нажмите **Environment Variables** (Переменные среды)
   - В разделе **System variables** (Системные переменные) найдите `Path`
   - Нажмите **Edit** (Изменить)
   - Нажмите **New** (Создать) и добавьте:
     ```
     C:\Program Files (x86)\GnuWin32\bin
     ```
   - Нажмите **OK** во всех окнах
   - Перезапустите PowerShell

4. **Проверьте снова:**
   ```powershell
   # Перезапустите PowerShell
   make --version
   ```

**Linux (Ubuntu/Debian):**

1. **Проверьте, где установлен make:**
   ```bash
   which make
   # Обычно: /usr/bin/make
   ```

2. **Если команда не найдена, переустановите:**
   ```bash
   sudo apt-get update
   sudo apt-get install --reinstall make
   ```

3. **Добавьте в PATH (если нужно):**
   ```bash
   # Откройте файл конфигурации
   nano ~/.bashrc
   
   # Добавьте строку:
   export PATH="/usr/bin:$PATH"
   
   # Сохраните (Ctrl+O, Enter, Ctrl+X)
   
   # Перезагрузите конфигурацию
   source ~/.bashrc
   ```

4. **Проверьте снова:**
   ```bash
   make --version
   ```

#### 🚨 Если Make всё ещё не работает

**Альтернатива 1: Используйте полный путь**

```bash
# macOS/Linux
/usr/bin/make all

# Windows
"C:\Program Files (x86)\GnuWin32\bin\make.exe" all
```

**Альтернатива 2: Используйте PowerShell-скрипты**

Для Windows без Make все команды доступны через скрипт `judge-run.ps1`, который не требует Make:

```powershell
pwsh -File .\scripts\judge-run.ps1
```

**Альтернатива 3: Ручные команды**

Если Make недоступен, вы можете выполнять команды вручную (см. раздел 2, Шаг 4, Вариант C).

**jq** *(для работы с JSON)*

| ОС | Установка |
|----|-----------|
| **macOS** | `brew install jq` |
| **Windows** | `winget install jqlang.jq` |
| **Linux** | `sudo apt-get install -y jq` |

> 💡 Проверьте установку: `jq --version`

---

### 0.3 Включите виртуализацию (если выключена)

#### Пошаговая инструкция:

1. **Перезагрузите ноутбук** и нажмите клавишу входа в BIOS/UEFI:
   - Обычно это `F2`, `F10`, `Delete` или `Esc`
   - Точная клавиша зависит от производителя (Dell, HP, Lenovo и т.д.)

2. **Найдите параметр виртуализации**:
   - **Intel**: ищите `Intel Virtualization Technology` или `Intel VT-x`
   - **AMD**: ищите `SVM Mode` или `AMD-V`
   - Обычно находится в разделе `Advanced`, `CPU Configuration` или `Security`

3. **Включите параметр**:
   - Измените значение на `Enabled`
   - Сохраните изменения (обычно `F10`)
   - Перезагрузитесь в операционную систему

4. **Проверьте результат**:

   **Windows:**
   ```powershell
   # PowerShell от администратора
   systeminfo | Select-String "Virtualization"
   ```
   Должно появиться: `Virtualization Enabled In Firmware: Yes`

   **macOS:**
   ```bash
   sysctl kern.hv_support
   ```
   Должно вернуть: `kern.hv_support: 1`

   **Linux:**
   ```bash
   egrep -c '(vmx|svm)' /proc/cpuinfo
   ```
   Должно вернуть число больше 0

5. **Включите WSL2** *(только для Windows, опционально)*:
   ```powershell
   # PowerShell от администратора
   wsl --install --no-distribution
   wsl --set-default-version 2
   ```
   - Перезагрузитесь
   - Откройте Microsoft Store и установите Ubuntu (если хотите работать в Linux-окружении)

> 💡 **Зачем нужен WSL2?** WSL2 предоставляет полноценное Linux-окружение в Windows, что упрощает работу с Kubernetes и Docker. Однако это опционально — PowerShell-скрипты также работают отлично.

---

### 0.4 Распакуйте архив и скопируйте `.env`

#### Структура архива:

После распаковки вы увидите следующую структуру:

```
ai-tourist/
├── gorkycode/              # Исходный код проекта
│   ├── services/           # Микросервисы
│   ├── helm/               # Helm чарты
│   ├── scripts/            # Автоматизационные скрипты
│   ├── Makefile            # Make-файл для автоматизации
│   └── ...
├── .env                    # ✨ Готовые секреты (НЕ коммитить!)
├── .env.example            # Шаблон для справки
└── docs/
    └── judges-deployment-guide.md
```

#### Инструкция по копированию:

1. **Распакуйте архив** в удобное место:
   - Windows: `C:\ai-tourist`
   - macOS/Linux: `~/ai-tourist`

2. **Скопируйте `.env`** в корень проекта `gorkycode/`:

   **macOS / Linux / WSL:**
   ```bash
   # Замените пути на актуальные
   cp /path/to/archive/.env /path/to/archive/gorkycode/.env
   
   # Пример:
   cp ~/ai-tourist/.env ~/ai-tourist/gorkycode/.env
   ```

   **Windows (PowerShell):**
   ```powershell
   # Замените пути на актуальные
   Copy-Item -LiteralPath "C:\ai-tourist\.env" -Destination "C:\ai-tourist\gorkycode\.env" -Force
   ```

3. **Проверьте результат**:

   **macOS / Linux / WSL:**
   ```bash
   ls -la gorkycode/.env
   ```

   **Windows (PowerShell):**
   ```powershell
   Get-Item -Path "gorkycode\.env" -Force
   ```

> ❗ **КРИТИЧЕСКИ ВАЖНО:** Без файла `.env` дальнейшие скрипты остановятся с ошибкой «.env not found». Убедитесь, что файл скопирован правильно.

> 🔧 **Проверка содержимого:** Файл `.env` должен содержать переменные вида:
> ```
> POSTGRES_USER=...
> POSTGRES_PASSWORD=...
> REDIS_HOST=...
> ```

---

### 0.5 Определите ваш сценарий запуска

Выберите подходящий сценарий в зависимости от вашей системы:

#### 🪟 Windows без WSL2 / без Hyper-V

**Подходит для:** Windows Home Edition, корпоративные ПК с ограничениями

**Требования:**
- PowerShell 7+
- VirtualBox (скачать с [virtualbox.org](https://www.virtualbox.org/wiki/Downloads))

**Драйвер:** `virtualbox`

**Команда запуска:**
```powershell
pwsh -File .\scripts\judge-run.ps1 -Driver virtualbox
```

> 💡 Скрипт `judge-run.ps1` автоматически добавит `GnuWin32`, `Chocolatey` и другие каталоги в `PATH`, чтобы `make` и другие утилиты сразу заработали.

#### 🪟 Windows с WSL2 (Ubuntu)

**Подходит для:** Windows Pro/Enterprise с включённым WSL2

**Требования:**
- WSL2 установлен и настроен
- Ubuntu или Debian внутри WSL

**Драйвер:** `docker` (работает через WSL2)

**Команда запуска:**
```bash
# Откройте терминал Ubuntu в WSL
cd /mnt/c/ai-tourist/gorkycode  # или ваш путь
./scripts/judge-run.sh
```

> 💡 **Преимущество WSL2:** Нативная Linux-среда, лучшая производительность, полная совместимость с Docker.

#### 🍎 macOS (Intel / Apple Silicon)

**Подходит для:** MacBook, iMac, Mac Mini

**Требования:**
- macOS 10.15+ (Catalina или новее)
- Homebrew установлен (`/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`)

**Драйвер:** 
- `docker` — если установлен Docker Desktop
- `virtualbox` — если Docker Desktop недоступен

**Команда запуска:**
```bash
# Terminal или iTerm2
cd ~/ai-tourist/gorkycode
./scripts/judge-run.sh
```

> 🔧 **Apple Silicon (M1/M2/M3):** Используйте Docker Desktop с поддержкой ARM64 или установите VirtualBox preview версии.

#### 🐧 Linux (Ubuntu / Debian)

**Подходит для:** Ubuntu 20.04+, Debian 11+

**Требования:**
- Стандартный Bash
- Sudo права для установки пакетов

**Драйвер:** 
- `docker` — если установлен Docker
- `virtualbox` — альтернатива
- `podman` — для систем без Docker

**Команда запуска:**
```bash
cd ~/ai-tourist/gorkycode
./scripts/judge-run.sh
```

> 💡 **Podman вместо Docker:**
> ```bash
> minikube start --driver=podman --cpus=4 --memory=8192 --disk-size=40g
> ```

---

## 1. Автопилот: всё за одну команду (рекомендуем)

Самый простой способ запустить проект — использовать автоматический скрипт.

### 1.1 Запуск автопилота

1. **Откройте терминал** и перейдите в папку проекта:
   ```bash
   cd /path/to/gorkycode
   # Пример для Windows: cd C:\ai-tourist\gorkycode
   # Пример для macOS/Linux: cd ~/ai-tourist/gorkycode
   ```

2. **Запустите скрипт `judge-run`**:

   **macOS / Linux / WSL:**
   ```bash
   ./scripts/judge-run.sh
   ```

   **Windows (PowerShell 7+, желательно «Run as Administrator»):**
   ```powershell
   pwsh -File .\scripts\judge-run.ps1
   ```

   > ⚠️ Если Docker Desktop недоступен, добавьте `-Driver virtualbox`:
   ```powershell
   pwsh -File .\scripts\judge-run.ps1 -Driver virtualbox
   ```

   > 🚨 **Если видите ошибку "Выполнение сценариев отключено" (PSSecurityException):**
   >
   > **Быстрое решение:**
   > ```powershell
   > # Разрешить скрипты для текущей сессии (НЕ требует прав админа)
   > Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
   > 
   > # Теперь запустите скрипт
   > .\scripts\judge-run.ps1
   > ```
   >
   > **Или запустите с bypass в одной команде:**
   > ```powershell
   > powershell -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1
   > ```
   >
   > **Для PowerShell 5.x** (если `pwsh` не работает):
   > ```powershell
   > powershell -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1
   > ```
   >
   > 💡 Подробнее об Execution Policy см. раздел 0.1 выше.

---

### 1.2 Что делает автопилот

Скрипт выполняет следующие шаги автоматически:

| Шаг | Что происходит | Что увидите в консоли | Примерное время |
|-----|----------------|------------------------|-----------------|
| **1. Проверка зависимостей** | Проверка наличия `minikube`, `kubectl`, `helm`, `docker` и `.env` файла | Сообщения `✅ Found: ...` или блок «Install tips» с командами установки | 10-30 сек |
| **2. Конвертация `.env`** | Создание `.env.yaml` и `helm/ai-tourist/secrets.yaml` из переменных окружения | `✅ Generated .env.yaml` и `✅ Generated secrets.yaml` | 5-10 сек |
| **3. Запуск Minikube** | Запуск или повторное использование существующего кластера Minikube | Вывод команды `minikube start --driver=... --cpus=... --memory=...` | 2-5 мин |
| **4. Сборка контейнеров** | Сборка Docker-образов внутри Minikube для всех сервисов | `🔧 Building backend...`, `🔧 Building frontend...`, и т.д. | 5-15 мин |
| **5. Деплой Helm-чарта** | Установка приложения в Kubernetes через Helm | Логи `helm upgrade --install ai-tourist ...` | 1-3 мин |
| **6. Smoke-тесты** | Запуск тестовых под для проверки работоспособности API | JSON-ответы от API endpoints | 30-60 сек |
| **7. Инструкции** | Вывод команд для настройки hosts и доступа к приложению | Подробные команды для вашей ОС | - |

> 💡 **Общее время выполнения:**
> - **Первый запуск:** 15–25 минут (Minikube скачивает образы Kubernetes, затем собираются контейнеры)
> - **Повторный запуск:** 5–8 минут (используются кэшированные образы)

---

### 1.3 Дополнительные флаги

Вы можете настроить поведение скрипта с помощью флагов:

#### Bash (macOS/Linux/WSL):

```bash
./scripts/judge-run.sh [OPTIONS]

OPTIONS:
  --driver <name>         Драйвер Minikube (docker/virtualbox/hyperv/podman)
  --env <path>            Путь к .env файлу (по умолчанию: .env в корне)
  --skip-checks           Пропустить проверку зависимостей
  --skip-build            Пропустить сборку контейнеров
  --skip-tests            Пропустить smoke-тесты
  --cpus <number>         Количество CPU для Minikube (по умолчанию: 6)
  --memory <size>         Объём памяти для Minikube (по умолчанию: 12g)
  --disk-size <size>      Размер диска для Minikube (по умолчанию: 40g)
```

**Примеры:**

```bash
# Использовать VirtualBox с уменьшенными ресурсами
./scripts/judge-run.sh --driver virtualbox --cpus 4 --memory 8g

# Кастомный путь к .env
./scripts/judge-run.sh --env /path/to/custom/.env

# Пропустить сборку (если уже собрано)
./scripts/judge-run.sh --skip-build
```

#### PowerShell (Windows):

```powershell
pwsh -File .\scripts\judge-run.ps1 [PARAMETERS]

PARAMETERS:
  -Driver <string>        Драйвер Minikube (docker/virtualbox/hyperv)
  -EnvFile <string>       Путь к .env файлу
  -SkipChecks            Пропустить проверку зависимостей
  -SkipBuild             Пропустить сборку контейнеров
  -SkipTests             Пропустить smoke-тесты
  -Cpus <int>            Количество CPU (по умолчанию: 6)
  -Memory <string>       Объём памяти (по умолчанию: 12g)
  -DiskSize <string>     Размер диска (по умолчанию: 40g)
```

**Примеры:**

```powershell
# Использовать VirtualBox
pwsh -File .\scripts\judge-run.ps1 -Driver virtualbox

# Уменьшенные ресурсы
pwsh -File .\scripts\judge-run.ps1 -Cpus 4 -Memory "8g"

# Пропустить все проверки и тесты (для отладки)
pwsh -File .\scripts\judge-run.ps1 -SkipChecks -SkipTests
```

---

### 1.4 Что делать после завершения

После успешного завершения скрипта:

#### Шаг 1: Настройте файл hosts

Скрипт выведет команду для вашей ОС. Выполните её:

**macOS / Linux / WSL:**
```bash
# Получите IP адрес Minikube
MINIKUBE_IP=$(minikube ip)

# Добавьте запись в hosts
echo "$MINIKUBE_IP ai-tourist.local" | sudo tee -a /etc/hosts
```

**Windows (PowerShell от администратора):**
```powershell
# Получите IP адрес Minikube
$MINIKUBE_IP = minikube ip

# Добавьте запись в hosts
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "$MINIKUBE_IP ai-tourist.local"
```

> 💡 **Проверьте результат:**
> ```bash
> ping ai-tourist.local
> ```

#### Шаг 2: Откройте приложение в браузере

Откройте браузер и перейдите по адресу:

```
http://ai-tourist.local
```

> 🔧 **Альтернатива без hosts:**
> Если изменить файл hosts нельзя, используйте port-forward:
> ```bash
> make port-forward в корне репозитория
> ```
> Затем откройте: `http://localhost:8080`

#### Шаг 3: Проверьте работоспособность

- Главная страница должна загрузиться
- API endpoints доступны на `http://ai-tourist.local/api/...`
- Логи можно посмотреть через:
  ```bash
  kubectl logs -n ai-tourist -l app=ai-tourist-backend
  ```

#### Шаг 4: Очистка после демонстрации

По окончании работы выполните:

**С установленным Make:**
```bash
make clean
minikube stop
```

**Windows без Make:**
```powershell
helm uninstall ai-tourist -n ai-tourist
kubectl delete namespace ai-tourist --force --grace-period=0
minikube stop
```

> 💡 **Полное удаление (включая Minikube):**
> ```bash
> minikube delete
> ```

---

## 2. Ручной сценарий (если автопилот попросил доустановить что-то)

Следующий план повторяет действия скрипта, но позволяет выполнять шаги по отдельности для лучшего контроля и отладки.

---

### Шаг 1. Диагностика окружения

Первым делом проверьте, что всё необходимое установлено:

**macOS / Linux / WSL:**
```bash
./scripts/setup-check.sh
```

**Windows (PowerShell 7+):**
```powershell
pwsh -File .\scripts\setup-check.ps1
```

> 🚨 **Если видите ошибку про Execution Policy:** используйте `powershell -ExecutionPolicy Bypass -File .\scripts\setup-check.ps1` или см. раздел 0.1

#### Что проверяет скрипт:

- ✅ Наличие `minikube`, `kubectl`, `helm`
- ✅ Наличие `docker` (опционально)
- ✅ Наличие `jq` для работы с JSON
- ✅ Наличие файла `.env` в корне проекта
- ✅ Достаточный объём свободного диска (минимум 20 ГБ)
- ✅ Версии установленных инструментов

#### Пример вывода:

```
🔍 Checking dependencies...
✅ Found: minikube (v1.32.0)
✅ Found: kubectl (v1.29.1)
✅ Found: helm (v3.14.0)
⚠️  Docker not found (optional, will use 'minikube image build')
✅ Found: jq (v1.7)
✅ Found: .env file
✅ Free disk space: 45 GB
```

#### Если чего-то не хватает:

Скрипт выведет блок **«Install tips»** с готовыми командами:

```
❌ Missing dependencies. Install tips:

macOS:
  brew install minikube kubectl helm jq

Windows (PowerShell as Admin):
  winget install Kubernetes.minikube Kubernetes.kubectl Kubernetes.Helm jqlang.jq

Linux (Ubuntu/Debian):
  sudo apt-get update
  sudo apt-get install -y kubectl jq
  curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
  sudo install minikube /usr/local/bin/
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

> 🔧 После установки недостающих утилит запустите проверку ещё раз, чтобы убедиться, что всё на месте.

---

### Шаг 2. Подготовка секретов

Конвертируйте `.env` файл в форматы, понятные Kubernetes:

**macOS / Linux / WSL:**
```bash
./scripts/env-to-yaml.sh
```

**Windows (PowerShell):**
```powershell
pwsh -File .\scripts\env-to-yaml.ps1
```

> 🚨 **Если видите ошибку про Execution Policy:** используйте `powershell -ExecutionPolicy Bypass -File .\scripts\env-to-yaml.ps1`

#### Что происходит:

1. Скрипт читает `.env` файл
2. Валидирует все обязательные переменные
3. Генерирует два YAML файла:
   - `.env.yaml` — в корне репозитория (используется Helm'ом)
   - `helm/ai-tourist/secrets.yaml` — резервная копия в чарте

#### Пример содержимого `.env.yaml`:

```yaml
POSTGRES_USER: "tourist_user"
POSTGRES_PASSWORD: "secure_password_123"
POSTGRES_DB: "tourist_db"
REDIS_HOST: "ai-tourist-redis"
REDIS_PORT: "6379"
JWT_SECRET: "very_secret_jwt_key"
ANTHROPIC_API_KEY: "sk-ant-..."
# ... остальные переменные
```

#### Обработка ошибок:

Если какая-то переменная пустая или отсутствует, скрипт остановится с сообщением:

```
❌ ERROR: Missing required environment variable: POSTGRES_PASSWORD
Please check your .env file and ensure all variables from .env.example are set.
```

> 💡 В этом случае откройте `.env` файл и заполните недостающие значения, сверяясь с `.env.example`.

---

### Шаг 3. Запустите Minikube

Запустите локальный Kubernetes кластер:

**Базовая команда (рекомендуется):**
```bash
minikube start --driver=docker --cpus=6 --memory=12g --disk-size=40g
```

#### Объяснение параметров:

| Параметр | Значение | Пояснение |
|----------|----------|-----------|
| `--driver` | `docker` | Драйвер виртуализации (см. альтернативы ниже) |
| `--cpus` | `6` | Количество CPU ядер для кластера |
| `--memory` | `12g` | Объём оперативной памяти (12 ГБ) |
| `--disk-size` | `40g` | Размер виртуального диска (40 ГБ) |

#### Альтернативные конфигурации:

**Windows без Hyper-V (использовать VirtualBox):**
```bash
minikube start --driver=virtualbox --cpus=4 --memory=8192 --disk-size=40g
```

> 💡 Предварительно установите VirtualBox с [virtualbox.org](https://www.virtualbox.org/wiki/Downloads)

**Linux с Podman:**
```bash
minikube start --driver=podman --cpus=4 --memory=8192 --disk-size=40g
```

**Минимальная конфигурация (для слабых ПК):**
```bash
minikube start --driver=docker --cpus=4 --memory=8192 --disk-size=30g
```

> ⚠️ При уменьшенных ресурсах некоторые сервисы могут работать медленнее или не запуститься.

#### Дополнительные параметры:

```bash
# Использовать конкретную версию Kubernetes
minikube start --kubernetes-version=v1.29.0 ...

# Включить дополнительные аддоны
minikube start ... --addons=metrics-server,ingress

# Использовать кастомную сеть
minikube start ... --network=custom-network

# Включить verbose логирование
minikube start --v=7 ...
```

#### Проверка статуса:

После запуска проверьте, что кластер работает:

```bash
# Статус Minikube
minikube status

# Информация о кластере
kubectl cluster-info

# Список нод
kubectl get nodes
```

**Ожидаемый вывод:**
```
minikube
type: Control Plane
host: Running
kubelet: Running
apiserver: Running
kubeconfig: Configured
```

> 💡 **Если Minikube не запустился:**
> - Проверьте логи: `minikube logs`
> - Удалите старый кластер и попробуйте снова: `minikube delete && minikube start ...`

---

### Шаг 4. Соберите и задеплойте сервисы

Теперь соберите Docker-образы и задеплойте приложение:

#### Вариант A: С установленным Make (рекомендуется)

**macOS / Linux / WSL:**

```bash
# Соберите образы и задеплойте
make all

# Покажите URL для доступа
make show-url
```

#### Что делает `make all`:

1. `make build` — собирает все Docker-образы:
   - `ai-tourist-backend`
   - `ai-tourist-frontend`
   - `ai-tourist-agent`
   - `ai-tourist-gateway`

2. `make deploy` — деплоит Helm-чарт:
   - Создаёт namespace `ai-tourist`
   - Устанавливает PostgreSQL
   - Устанавливает Redis
   - Деплоит все микросервисы
   - Создаёт Ingress для доступа

3. `make test-smoke` — запускает smoke-тесты:
   - Проверяет доступность API
   - Валидирует ответы endpoints

#### Вариант B: Без Make (Windows PowerShell)

**Windows (PowerShell):**

```powershell
# 1. Конвертируйте .env (если ещё не делали)
pwsh -File .\scripts\env-to-yaml.ps1

# 2. Запустите полный цикл
pwsh -File .\scripts\judge-run.ps1 -SkipChecks [-Driver virtualbox]
```

> 💡 `-SkipChecks` пропускает проверку зависимостей (используйте только если уже проверяли на шаге 1)

#### Вариант C: Ручные команды (для полного контроля)

Если хотите выполнять каждый шаг вручную:

```bash
# 1. Настройте Docker окружение на Minikube
eval $(minikube docker-env)

# 2. Соберите backend
docker build -t ai-tourist-backend:latest ./services/backend

# 3. Соберите frontend
docker build -t ai-tourist-frontend:latest ./services/frontend

# 4. Соберите agent
docker build -t ai-tourist-agent:latest ./services/agent

# 5. Соберите gateway
docker build -t ai-tourist-gateway:latest ./services/gateway

# 6. Задеплойте через Helm
helm upgrade --install ai-tourist ./helm/ai-tourist \
  --namespace ai-tourist \
  --create-namespace \
  --set-file secrets=.env.yaml \
  --timeout 10m \
  --wait
```

> 🔧 **Если Docker CLI недоступен**, используйте `minikube image build`:
> ```bash
> minikube image build -t ai-tourist-backend:latest ./services/backend
> minikube image build -t ai-tourist-frontend:latest ./services/frontend
> # ... и так далее
> ```

#### Проверка результата:

Дождитесь, пока все поды запустятся:

```bash
# Смотрите статус подов
kubectl get pods -n ai-tourist

# Следите за логами в реальном времени
kubectl get pods -n ai-tourist --watch
```

**Ожидаемый вывод:**
```
NAME                                      READY   STATUS    RESTARTS   AGE
ai-tourist-backend-7d8f9b6c5d-x4k2m      1/1     Running   0          2m
ai-tourist-frontend-5c7b8d9f6a-p9n7q     1/1     Running   0          2m
ai-tourist-agent-6f8d7c9e5b-m3k8w        1/1     Running   0          2m
ai-tourist-gateway-8g9e7d8f6c-q5p2r      1/1     Running   0          2m
ai-tourist-postgresql-0                   1/1     Running   0          3m
ai-tourist-redis-master-0                 1/1     Running   0          3m
```

> ⚠️ **Если под в статусе `ImagePullBackOff` или `ErrImagePull`:**
> - Проверьте, что образы собраны: `minikube image ls | grep ai-tourist`
> - Пересоберите образы: `make build` или вручную через `docker build`

---

### Шаг 5. Откройте приложение

После успешного деплоя настройте доступ к приложению.

#### Вариант A: Через файл hosts (рекомендуется)

**1. Получите IP адрес Minikube:**

```bash
minikube ip
# Пример вывода: 192.168.49.2
```

**2. Добавьте запись в hosts:**

**macOS / Linux / WSL:**
```bash
# Автоматически
echo "$(minikube ip) ai-tourist.local" | sudo tee -a /etc/hosts

# Или вручную отредактируйте файл
sudo nano /etc/hosts
# Добавьте строку: 192.168.49.2 ai-tourist.local
```

**Windows (PowerShell от администратора):**
```powershell
# Автоматически
$MINIKUBE_IP = minikube ip
Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "$MINIKUBE_IP ai-tourist.local"

# Или вручную отредактируйте файл
notepad C:\Windows\System32\drivers\etc\hosts
# Добавьте строку: 192.168.49.2 ai-tourist.local
```

**3. Проверьте доступность:**

```bash
# Ping домена
ping ai-tourist.local

# Или через curl
curl http://ai-tourist.local/api/health
```

**4. Откройте в браузере:**

```
http://ai-tourist.local
```

#### Вариант B: Через port-forward (если hosts недоступен)

Если изменить файл hosts нельзя (корпоративные ограничения), используйте port-forward:

```bash
# Пробросьте порт frontend
kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80

# В отдельном терминале пробросьте порт gateway
kubectl port-forward -n ai-tourist svc/ai-tourist-gateway 8081:80
```

**Откройте в браузере:**
- Frontend: `http://localhost:8080`
- API Gateway: `http://localhost:8081/api/...`

> 💡 **Port-forward должен работать в фоне.** Не закрывайте терминал, пока пользуетесь приложением.

#### Вариант C: Через NodePort

Если нужен более стабильный доступ без изменения hosts:

```bash
# Получите NodePort для frontend
kubectl get svc -n ai-tourist ai-tourist-frontend -o jsonpath='{.spec.ports[0].nodePort}'

# Пример вывода: 30080

# Откройте в браузере
http://$(minikube ip):30080
```

#### Проверка работоспособности:

Выполните несколько тестовых запросов:

```bash
# Health check
curl http://ai-tourist.local/api/health
# Ожидается: {"status":"ok"}

# Список туров (если есть данные)
curl http://ai-tourist.local/api/tours

# Информация о версии
curl http://ai-tourist.local/api/version
```

---

### Шаг 6. Очистка после проверки

По завершении демонстрации удалите развёрнутое приложение.

#### Вариант A: С Make

```bash
# Удалить приложение, сохранив Minikube
make clean

# Остановить Minikube
minikube stop

# Полное удаление Minikube (включая данные)
minikube delete
```

#### Вариант B: Без Make (Windows PowerShell или любая ОС)

```bash
# Удалить Helm release
helm uninstall ai-tourist -n ai-tourist

# Удалить namespace (форсированно, чтобы не ждать graceful shutdown)
kubectl delete namespace ai-tourist --force --grace-period=0

# Остановить Minikube
minikube stop

# Полное удаление Minikube
minikube delete
```

#### Очистка Docker образов (опционально)

Если нужно освободить место:

```bash
# Удалить неиспользуемые образы
docker image prune -a

# Удалить всё (образы, контейнеры, volumes)
docker system prune -a --volumes
```

> ⚠️ **Внимание:** `docker system prune -a --volumes` удалит ВСЕ Docker данные, не только связанные с проектом.

---

## 3. Частые проблемы и решения

Подробный troubleshooting guide с решениями типичных проблем.

---

### 🚨 Проблемы с установкой и зависимостями

#### ❌ PowerShell: "Выполнение сценариев отключено" (Execution Policy)

**Симптомы:**
```
Невозможно загрузить файл C:\...\judge-run.ps1, так как выполнение сценариев отключено в этой системе
PSSecurityException
UnauthorizedAccess
FullyQualifiedErrorId : UnauthorizedAccess
```

**Причина:**
Windows блокирует выполнение `.ps1` скриптов из соображений безопасности.

**Решение (выберите любой):**

**Вариант 1: Самый быстрый (БЕЗ прав администратора)**
```powershell
# Разрешить только для текущей сессии
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Теперь запустите скрипт
cd C:\Users\Ya\Desktop\gorkycode
.\scripts\judge-run.ps1
```

**Вариант 2: Запуск с bypass в одной команде**
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\judge-run.ps1
```

**Вариант 3: Постоянное разрешение (требует админа)**
```powershell
# От имени администратора
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Подтвердите (Y), затем перезапустите PowerShell
```

**Вариант 4: Unblock конкретного файла**
```powershell
Unblock-File -Path .\scripts\judge-run.ps1
.\scripts\judge-run.ps1
```

> 💡 **Рекомендуется Вариант 1** — безопасно и не требует прав администратора!

> 📖 Подробное объяснение всех методов см. в разделе 0.1

---

#### ❌ `minikube` не установлен

**Симптомы:**
```
command not found: minikube
'minikube' is not recognized as an internal or external command
```

**Решение:**

1. Установите Minikube для вашей ОС:
   - **macOS:** `brew install minikube`
   - **Windows:** `winget install Kubernetes.minikube`
   - **Linux:** см. раздел 0.2

2. Перезапустите терминал

3. Проверьте установку:
   ```bash
   minikube version
   ```

4. Если команда всё ещё не найдена, проверьте PATH:
   ```bash
   # macOS/Linux
   echo $PATH | tr ':' '\n' | grep -i minikube
   
   # Windows PowerShell
   $env:PATH -split ';' | Select-String minikube
   ```

#### ❌ Виртуализация выключена

**Симптомы:**
```
Exiting due to HOST_VIRT_UNAVAILABLE: Failed to start host: ...
This computer doesn't have VT-X/AMD-v enabled
```

**Решение:**

1. **Включите в BIOS/UEFI** (см. детали в разделе 0.3):
   - Перезагрузите компьютер
   - Войдите в BIOS (F2, F10, Delete)
   - Найдите `Intel VT-x` или `AMD-V`
   - Установите `Enabled`
   - Сохраните и перезагрузитесь

2. **Проверьте результат:**

   **Windows:**
   ```powershell
   systeminfo | Select-String "Virtualization"
   # Ожидается: Virtualization Enabled In Firmware: Yes
   ```

   **macOS:**
   ```bash
   sysctl kern.hv_support
   # Ожидается: kern.hv_support: 1
   ```

   **Linux:**
   ```bash
   egrep -c '(vmx|svm)' /proc/cpuinfo
   # Ожидается: число > 0
   ```

3. **Если виртуализация всё ещё недоступна:**
   - Проверьте, не блокирует ли антивирус
   - На Windows: убедитесь, что Hyper-V не конфликтует с VirtualBox
   - Попробуйте другой драйвер (например, `podman`)

---

### 🚨 Проблемы с ресурсами

#### ⚠️ Недостаточно дискового пространства

**Симптомы:**
```
Error: insufficient disk space
Requested disk size: 40GB, Available: 15GB
```

**Решение:**

1. **Очистите диск:**

   **Удалите старые Docker образы:**
   ```bash
   docker system prune -af
   docker volume prune -f
   ```

   **Удалите старые Minikube кластеры:**
   ```bash
   minikube delete --all
   ```

   **Очистите системный кэш:**
   - **Windows:** Disk Cleanup (Очистка диска)
   - **macOS:** Удалите `~/Library/Caches`
   - **Linux:** `sudo apt-get clean && sudo apt-get autoclean`

2. **Уменьшите требования:**
   ```bash
   minikube start --driver=docker --cpus=4 --memory=8g --disk-size=25g
   ```

3. **Используйте внешний диск** (если доступен):
   ```bash
   # Переместите Minikube профиль
   minikube delete
   export MINIKUBE_HOME=/path/to/external/drive
   minikube start ...
   ```

#### ⚠️ Недостаточно оперативной памяти

**Симптомы:**
```
Pods in CrashLoopBackOff or OOMKilled
Error: Failed to allocate memory
```

**Решение:**

1. **Закройте лишние приложения** (браузеры, IDE, и т.д.)

2. **Уменьшите выделяемую память:**
   ```bash
   minikube stop
   minikube delete
   minikube start --driver=docker --cpus=4 --memory=8g
   ```

3. **Отключите ненужные сервисы в Helm:**
   ```bash
   helm upgrade ai-tourist ./helm/ai-tourist \
     --set redis.enabled=false \
     --set monitoring.enabled=false
   ```

---

### 🚨 Проблемы с Docker

#### ❌ Docker Desktop недоступен

**Симптомы:**
```
Cannot connect to the Docker daemon
docker: command not found
```

**Решение:**

**Вариант 1: Установите Docker Desktop**
- [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/)

**Вариант 2: Используйте VirtualBox (без Docker)**

1. Установите VirtualBox:
   - **macOS:** `brew install --cask virtualbox`
   - **Windows:** [virtualbox.org/wiki/Downloads](https://www.virtualbox.org/wiki/Downloads)
   - **Linux:** `sudo apt-get install -y virtualbox`

2. Запустите Minikube с драйвером VirtualBox:
   ```bash
   minikube start --driver=virtualbox --cpus=4 --memory=8192
   ```

3. Скрипты автоматически переключатся на `minikube image build` вместо `docker build`

**Вариант 3: Используйте Podman (Linux)**
```bash
sudo apt-get install -y podman
minikube start --driver=podman --cpus=4 --memory=8192
```

---

### 🚨 Проблемы с сертификатами

#### ❌ `certificate signed by unknown authority`

**Симптомы:**
```
Error: x509: certificate signed by unknown authority
Failed to pull image
TLS handshake timeout
```

**Решение:**

1. **Проверьте дату и время системы:**
   - Неправильное время — частая причина проблем с сертификатами
   - Синхронизируйте часы с интернетом

2. **Перезапустите Minikube:**
   ```bash
   minikube delete
   minikube start --driver=docker --cpus=6 --memory=12g
   ```

3. **Отключите прокси** (если используется корпоративный прокси):
   ```bash
   unset HTTP_PROXY HTTPS_PROXY NO_PROXY
   minikube start ...
   ```

4. **Добавьте доверенные сертификаты** (для корпоративных сетей):
   ```bash
   minikube start \
     --insecure-registry="your-registry.com" \
     --embed-certs
   ```

---

### 🚨 Проблемы с сетью и доступом

#### ⚠️ Веб-интерфейс не открывается по `ai-tourist.local`

**Симптомы:**
```
This site can't be reached
ERR_NAME_NOT_RESOLVED
```

**Решение:**

**1. Проверьте файл hosts:**

```bash
# macOS/Linux
cat /etc/hosts | grep ai-tourist

# Windows PowerShell
Get-Content C:\Windows\System32\drivers\etc\hosts | Select-String "ai-tourist"
```

Должна быть строка вида:
```
192.168.49.2 ai-tourist.local
```

**2. Перепроверьте IP Minikube:**
```bash
minikube ip
```

Если IP изменился, обновите hosts:

```bash
# macOS/Linux
sudo sed -i '' 's/^[0-9.]* ai-tourist.local/$(minikube ip) ai-tourist.local/' /etc/hosts

# Windows PowerShell
$content = Get-Content C:\Windows\System32\drivers\etc\hosts
$newIP = minikube ip
$content = $content -replace '^\d+\.\d+\.\d+\.\d+ ai-tourist\.local', "$newIP ai-tourist.local"
Set-Content -Path C:\Windows\System32\drivers\etc\hosts -Value $content
```

**3. Используйте port-forward как альтернативу:**
```bash
kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80
```
Откройте: `http://localhost:8080`

**4. Проверьте Ingress:**
```bash
kubectl get ingress -n ai-tourist
kubectl describe ingress -n ai-tourist ai-tourist-ingress
```

---

### 🚨 Проблемы с подами

#### ❌ Smoke-тесты не проходят

**Симптомы:**
```
❌ Smoke tests failed
Pod ai-tourist-test-xxxx failed
CrashLoopBackOff
```

**Решение:**

**1. Проверьте логи тестового пода:**
```bash
# Найдите имя пода
kubectl get pods -n ai-tourist | grep test

# Посмотрите логи
kubectl logs -n ai-tourist ai-tourist-test-xxxxx
```

**2. Проверьте статус всех подов:**
```bash
kubectl get pods -n ai-tourist
```

Если какие-то поды в `CrashLoopBackOff`:

```bash
# Посмотрите детали
kubectl describe pod -n ai-tourist <POD_NAME>

# Посмотрите логи
kubectl logs -n ai-tourist <POD_NAME> --previous
```

**3. Типичные причины:**

- **Backend не может подключиться к БД:**
  ```bash
  # Проверьте, что PostgreSQL запущен
  kubectl get pods -n ai-tourist | grep postgresql
  
  # Проверьте переменные окружения
  kubectl get secret -n ai-tourist ai-tourist-secrets -o yaml
  ```

- **Redis недоступен:**
  ```bash
  # Проверьте Redis
  kubectl get pods -n ai-tourist | grep redis
  
  # Посмотрите логи Redis
  kubectl logs -n ai-tourist ai-tourist-redis-master-0
  ```

- **Неправильные секреты:**
  ```bash
  # Пересоздайте секреты
  ./scripts/env-to-yaml.sh  # или .ps1 для Windows
  
  # Обновите деплоймент
  helm upgrade ai-tourist ./helm/ai-tourist \
    --set-file secrets=.env.yaml \
    --reuse-values
  ```

**4. Перезапустите деплоймент:**
```bash
# Удалите неработающие поды
kubectl delete pod -n ai-tourist -l app=ai-tourist-backend

# Или полностью пересоберите
make clean
make all
```

---

## 4. Дополнительные сценарии

### 4.1 Работа внутри виртуальной машины

Если корпоративная политика запрещает устанавливать Docker/VirtualBox напрямую на рабочую станцию, можно использовать отдельную виртуальную машину.

#### Создание VM:

**1. Установите гипервизор:**
- VirtualBox (рекомендуется): [virtualbox.org](https://www.virtualbox.org/wiki/Downloads)
- VMware Workstation Player (альтернатива)
- Hyper-V (встроен в Windows Pro)

**2. Скачайте ISO образ:**
- Ubuntu 22.04 LTS: [ubuntu.com/download/desktop](https://ubuntu.com/download/desktop)
- Debian 11: [debian.org/distrib](https://www.debian.org/distrib/)

**3. Создайте виртуальную машину с параметрами:**

| Параметр | Минимум | Рекомендуется |
|----------|---------|---------------|
| **CPU** | 4 ядра | 6-8 ядер |
| **RAM** | 8 ГБ | 12-16 ГБ |
| **Диск** | 30 ГБ | 50 ГБ |
| **Сеть** | Bridged Adapter | Bridged Adapter |

**4. Установите ОС:**
- Следуйте инструкциям установщика
- Создайте пользователя с sudo правами
- Обновите систему:
  ```bash
  sudo apt-get update && sudo apt-get upgrade -y
  ```

#### Настройка VM:

**1. Установите зависимости** (см. раздел 0.2, колонка Ubuntu/Debian):

```bash
# Обновите пакеты
sudo apt-get update

# Установите необходимые инструменты
sudo apt-get install -y curl conntrack jq make

# Установите Minikube
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube /usr/local/bin/

# Установите kubectl
sudo apt-get install -y kubectl

# Установите Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Установите Docker (опционально)
sudo apt-get install -y docker.io
sudo usermod -aG docker $USER
newgrp docker
```

**2. Скопируйте проект в VM:**

**Вариант A: Через Shared Folders**

В VirtualBox:
1. `Devices` → `Shared Folders` → `Shared Folder Settings`
2. Добавьте папку с проектом
3. В VM смонтируйте:
   ```bash
   sudo mkdir /mnt/shared
   sudo mount -t vboxsf ai-tourist /mnt/shared
   cp -r /mnt/shared ~/ai-tourist
   ```

**Вариант B: Через SCP**

С вашего компьютера:
```bash
# Узнайте IP виртуальной машины
# В VM выполните: ip a

# Скопируйте архив
scp -r /path/to/ai-tourist username@VM_IP:~/

# Подключитесь к VM
ssh username@VM_IP
```

**Вариант C: Через Git**

Если проект в приватном репозитории:
```bash
# В VM
git clone https://github.com/your-org/ai-tourist.git
cd ai-tourist
# Скопируйте .env файл вручную
```

**3. Запустите проект внутри VM:**

```bash
cd ~/ai-tourist/gorkycode
./scripts/judge-run.sh
```

**4. Доступ к приложению из основной ОС:**

```bash
# Получите IP адрес VM
hostname -I  # Например: 192.168.1.50

# Добавьте в hosts на ОСНОВНОЙ машине (не в VM!)
echo "192.168.1.50 ai-tourist.local" | sudo tee -a /etc/hosts

# Откройте в браузере на основной машине
http://ai-tourist.local
```

---

### 4.2 Перезапуск с нуля

Если что-то пошло не так и нужно начать заново:

#### Полная очистка:

```bash
# 1. Удалите Helm release
helm uninstall ai-tourist -n ai-tourist 2>/dev/null || true

# 2. Удалите namespace
kubectl delete namespace ai-tourist --force --grace-period=0 2>/dev/null || true

# 3. Остановите Minikube
minikube stop

# 4. Удалите Minikube кластер полностью
minikube delete

# 5. Очистите Docker образы (опционально)
docker system prune -af --volumes 2>/dev/null || true

# 6. Удалите сгенерированные файлы
rm -f .env.yaml helm/ai-tourist/secrets.yaml
```

#### Свежий старт:

```bash
# 1. Убедитесь, что .env на месте
ls -la gorkycode/.env

# 2. Запустите автопилот заново
./scripts/judge-run.sh

# Или для Windows PowerShell:
pwsh -File .\scripts\judge-run.ps1
```

> 💡 После полной очистки первый запуск займёт больше времени, так как Minikube заново скачает базовые образы Kubernetes.

---

## 5. Контакты и поддержка

Если ни один из сценариев не помог, свяжитесь с командой разработки.

### Что предоставить при обращении:

1. **Информация о системе:**
   ```bash
   # Соберите системную информацию
   echo "OS: $(uname -s) $(uname -r)"
   echo "Minikube: $(minikube version --short)"
   echo "Kubectl: $(kubectl version --client --short)"
   echo "Helm: $(helm version --short)"
   echo "Docker: $(docker --version 2>/dev/null || echo 'N/A')"
   ```

2. **Используемый драйвер:**
   ```bash
   minikube profile list
   ```

3. **Логи последней команды:**
   - Скопируйте полный вывод терминала
   - Или сохраните в файл:
     ```bash
     ./scripts/judge-run.sh 2>&1 | tee deployment-log.txt
     ```

4. **Статус подов** (если проект частично развёрнут):
   ```bash
   kubectl get pods -n ai-tourist
   kubectl get events -n ai-tourist --sort-by='.lastTimestamp'
   ```

5. **Конфигурация Minikube:**
   ```bash
   minikube config view
   ```

> 💡 Это поможет быстро подсказать дальнейшие действия.

---

## 🎉 Финал

Поздравляем! Вы прошли полное руководство по развёртыванию AI Tourist.

### Быстрый чеклист для судей:

- ✅ Установлены зависимости (Minikube, kubectl, Helm)
- ✅ Включена виртуализация в BIOS
- ✅ Файл `.env` скопирован в `gorkycode/`
- ✅ Запущен скрипт `judge-run.sh` или `judge-run.ps1`
- ✅ Добавлена запись в hosts: `<MINIKUBE_IP> ai-tourist.local`
- ✅ Приложение открывается в браузере: `http://ai-tourist.local`
- ✅ API отвечает корректно: `curl http://ai-tourist.local/api/health`

### Что делать дальше:

1. **Протестируйте приложение** — проверьте основные функции
2. **Посмотрите логи** — убедитесь, что нет ошибок
3. **Остановите и очистите** — выполните `make clean` и `minikube stop`

**Удачной проверки!** 
