# 🧭 AI Tourist — Judge Deployment Runbook

Этот документ — максимально подробный план, который позволит запустить проект даже человеку без опыта в Docker/Kubernetes. Читайте разделы по порядку и выполняйте шаги один за другим. Никаких дополнительных секретов или ручных настроек не требуется — всё уже лежит в архиве.

## 🔖 Легенда

- ✅ — всё хорошо, переходите дальше.
- ⚠️ — предупреждение. Можно продолжать, но лучше выполнить рекомендацию.
- ❌ — критичная проблема. Остановитесь, исправьте ошибку и повторите шаг.
- 💡 — полезные подсказки.

## 0. Предварительная подготовка (один раз на ноутбуке)

### 0.1 Выберите, откуда запускать команды

| ОС | Рекомендуемая оболочка |
|----|------------------------|
| macOS | Встроенный Terminal или iTerm2 |
| Windows 10/11 | **PowerShell 7** (запускайте «Run as Administrator» для установки зависимостей) |
| Windows с WSL2 | Терминал Ubuntu/Debian внутри WSL2 (инструкции см. ниже) |
| Linux (Ubuntu/Debian) | Любой терминал Bash |

> 💡 **PowerShell 7** уже входит в Windows 11. Если у вас PowerShell 5, скачайте [последнюю версию](https://github.com/PowerShell/PowerShell/releases) и установите её.

### 0.2 Установите требуемые инструменты

| Инструмент | macOS | Windows 10/11 (PowerShell) | Ubuntu / Debian |
|------------|-------|----------------------------|-----------------|
| **Virtualization / Hypervisor** | Включено по умолчанию. Проверка: `sysctl kern.hv_support` → `1`. | BIOS/UEFI → включите Intel VT-x / AMD-V. Если Hyper-V недоступен (Windows Home), просто включите виртуализацию для VirtualBox. | BIOS/UEFI → включите Intel VT-x / AMD-V. |
| **Minikube** | `brew install minikube` | `winget install Kubernetes.minikube` | ```bash
sudo apt-get update && sudo apt-get install -y curl conntrack
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube /usr/local/bin/
``` |
| **kubectl** | `brew install kubectl` | `winget install Kubernetes.kubectl` | `sudo apt-get install -y kubectl` |
| **Helm** | `brew install helm` | `winget install Kubernetes.Helm` | `curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash` |
| **Docker Desktop** *(по желанию)* | [docker.com](https://www.docker.com/products/docker-desktop/) | [docker.com](https://www.docker.com/products/docker-desktop/)  Если нельзя ставить Docker Desktop, используйте VirtualBox + `--driver=virtualbox`. | `sudo apt-get install -y docker.io` или используйте `minikube image build` без Docker. |
| **VirtualBox** *(если без Docker)* | `brew install --cask virtualbox` (потребуется перезагрузка) | [virtualbox.org](https://www.virtualbox.org/wiki/Downloads) | `sudo apt-get install -y virtualbox` |
| **Make** *(опционально)* | Входит в Xcode CLT: `xcode-select --install` | `winget install GnuWin32.Make` или `choco install make` (скрипт сам добавит `C:\\Program Files (x86)\\GnuWin32\\bin` в PATH) | `sudo apt-get install -y make` |
| **jq** | `brew install jq` | `winget install jqlang.jq` | `sudo apt-get install -y jq` |

> ⚠️ **Если нельзя установить Docker Desktop.** Это нормально. Скрипты автоматически переключаются на `minikube image build`, достаточно иметь Minikube + VirtualBox/Podman.

### 0.3 Включите виртуализацию (если выключена)

1. Перезагрузите ноутбук и нажмите клавишу входа в BIOS/UEFI (обычно F2, F10, Delete).
2. Найдите пункт **Intel Virtualization Technology**, **Intel VT-x**, **SVM Mode** или **AMD-V**. Выставьте **Enabled**.
3. Сохраните изменения, загрузитесь в ОС.
4. На Windows запустите PowerShell от администратора и выполните:
   ```powershell
   systeminfo | Select-String "Virtualization"
   ```
   Если увидите `Virtualization Enabled In Firmware: Yes` — всё в порядке.
5. При необходимости включите WSL2:
   ```powershell
   wsl --install --no-distribution
   wsl --set-default-version 2
   ```
   Перезагрузитесь, откройте Microsoft Store и установите Ubuntu (если хотите работать внутри Linux среды).

### 0.4 Распакуйте архив и скопируйте `.env`

1. Разархивируйте архив в удобное место (например, `C:\ai-tourist` или `~/ai-tourist`).
2. Внутри будут:
   - папка `gorkycode/` — исходный код проекта;
   - файл `.env` с готовыми секретами (его нельзя коммитить в git);
   - этот документ `docs/judges-deployment-guide.md`;
   - файл `.env.example` — для справки и ручных правок.
3. **Скопируйте `.env` в корень проекта `gorkycode/`.**
   - macOS / Linux / WSL:
     ```bash
     cp /path/to/archive/.env /path/to/archive/gorkycode/.env
     ```
   - Windows (PowerShell):
     ```powershell
     Copy-Item -LiteralPath "C:\ai-tourist\.env" -Destination "C:\ai-tourist\gorkycode\.env" -Force
     ```
   - Если файлы лежат в другом месте, подставьте свои пути. Главное — чтобы `.env` оказался рядом с `Makefile`.

> ❗ Без этого шага дальнейшие скрипты остановятся с ошибкой «.env not found».

### 0.5 Определите ваш сценарий запуска

- **Windows без WSL2 / без Hyper-V.** Используйте PowerShell 7 и драйвер `virtualbox` (установите VirtualBox). Скрипт `judge-run.ps1` подскажет нужные команды и временно добавит `GnuWin32`, `Chocolatey` и другие каталоги в `PATH`, чтобы `make` сразу заработал.
- **Windows с WSL2 (Ubuntu).** Откройте терминал Ubuntu внутри WSL, выполните команды из Linux-раздела (Bash-скрипты). Если WSL2 ещё не установлен, см. шаг 0.3 (`wsl --install --no-distribution`).
- **macOS (Intel/Apple Silicon).** Работайте из Terminal/iTerm2. Драйвер `docker` подходит, но на Mac без Docker Desktop используйте `--driver=virtualbox`.
- **Linux (Ubuntu/Debian).** Любой Bash-терминал. Если Docker недоступен, установите VirtualBox или Podman и используйте соответствующий драйвер.

> 💡 Во всех сценариях вспомогательные скрипты автоматически добавляют популярные каталоги (`brew`, `~/.local/bin` и др.) во временный `PATH`, поэтому только что установленные утилиты сразу находятся в текущем окне терминала.

## 1. Автопилот: всё за одну команду (рекомендуем)

1. Откройте терминал и перейдите в папку `gorkycode`:
   ```bash
   cd /path/to/gorkycode
   ```
2. Запустите скрипт **judge-run**:
   - macOS / Linux / WSL:
     ```bash
     ./scripts/judge-run.sh
     ```
   - Windows (PowerShell 7+, желательно «Run as Administrator»):
     ```powershell
     pwsh -File .\scripts\judge-run.ps1
     ```
      Если Docker Desktop недоступен, добавьте `-Driver virtualbox` (при установленном VirtualBox). Когда Hyper-V/WSL2 включены, можно оставить драйвер по умолчанию (`docker`).

Скрипт делает всё подряд:

| Шаг | Что происходит | Что увидеть в консоли |
|-----|----------------|------------------------|
| 1 | Проверка зависимостей и `.env` | Сообщения `✅` или подсказки с командами установки |
| 2 | Конвертация `.env` | Создание `.env.yaml` и `helm/ai-tourist/secrets.yaml` |
| 3 | Запуск или повторное использование Minikube | Печатается точная команда `minikube start ...` |
| 4 | Сборка контейнеров внутри Minikube | Сообщения `🔧 Building ...` |
| 5 | Деплой Helm-чарта | Логи `helm upgrade --install ...` |
| 6 | Smoke-тесты | Поды curl делают запросы, выводится JSON |
| 7 | Инструкция по hosts/port-forward | Подробные команды для macOS/Linux/Windows |

> 💡 **Время выполнения.** Первый запуск может занять 15–25 минут: Minikube скачивает образы Kubernetes, затем собираются контейнеры. Повторный запуск — 5–8 минут.

### 1.1 Дополнительные флаги

- `--driver virtualbox` (Bash) / `-Driver virtualbox` (PowerShell) — принудительно выбрать драйвер (актуально для Windows Home без Hyper-V).
- `--env /путь/к/.env` — если `.env` лежит не в корне репозитория.
- `--skip-checks`, `--skip-build`, `--skip-tests` — пропустить соответствующие этапы (используйте только если уверены, что шаг уже выполнен).

### 1.2 Что делать после завершения

1. Добавьте строку в файл hosts (скрипт подскажет точную команду).
2. Откройте `http://ai-tourist.local` в браузере.
3. По окончании демонстрации выполните:
   - `make clean` (или на Windows без Make — команды из раздела 2.6);
   - `minikube stop`.

## 2. Ручной сценарий (если автопилот попросил доустановить что-то)

Следующий план повторяет действия скрипта, но позволяет выполнять шаги по отдельности.

### Шаг 1. Диагностика окружения

- macOS / Linux / WSL:
  ```bash
  ./scripts/setup-check.sh
  ```
- Windows (PowerShell 7+):
  ```powershell
  pwsh -File .\scripts\setup-check.ps1
  ```

Скрипт проверит наличие инструментов, достаточный объём диска, правильность `.env`. Если чего-то не хватает, в консоли появится блок «Install tips» с готовыми командами. После установки недостающих утилит запустите проверку ещё раз.

### Шаг 2. Подготовка секретов

```bash
# macOS / Linux / WSL
./scripts/env-to-yaml.sh
```

```powershell
# Windows (PowerShell)
pwsh -File .\scripts\env-to-yaml.ps1
```

Результат:
- `.env.yaml` в корне репозитория (используется Helm’ом);
- `helm/ai-tourist/secrets.yaml` (резервная копия в чарте).

Если какая-то переменная пустая, скрипт остановится и подскажет, что нужно заполнить (см. `.env.example`).

### Шаг 3. Запустите Minikube

```bash
minikube start --driver=docker --cpus=6 --memory=12g --disk-size=40g
```

Альтернативы:
- Windows без Hyper-V — `--driver=virtualbox --cpus=4 --memory=8192` (предварительно установите VirtualBox).
- Linux с Podman — `--driver=podman --cpus=4 --memory=8192 --disk-size=40g`.
- Если ресурсов мало, временно уменьшите параметры до `--cpus=4 --memory=8192`.

### Шаг 4. Соберите и задеплойте сервисы

**macOS / Linux / WSL (с установленным make):**
```bash
make all
make show-url
```

**Windows без Make:**
```powershell
pwsh -File .\scripts\env-to-yaml.ps1   # если ещё не запускали
pwsh -File .\scripts\judge-run.ps1 -SkipChecks [-Driver virtualbox]
```

> 💡 Уточните драйвер: оставьте значение по умолчанию (`docker`), если Docker Desktop/WSL2 работают, или добавьте `-Driver virtualbox`, когда используете VirtualBox.

> 💡 Если нет Docker CLI, команды автоматически переключаются на `minikube image build` — ничего дополнительно настраивать не нужно.

### Шаг 5. Откройте приложение

1. Добавьте строку `MINIKUBE_IP ai-tourist.local` в файл hosts (см. подсказки скрипта или раздел 1.2).
2. Откройте `http://ai-tourist.local`.
3. Если править hosts нельзя, выполните `kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80` и заходите на `http://localhost:8080`.

### Шаг 6. Очистка после проверки

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

## 3. Частые проблемы и решения

| Проблема | Что делать |
|----------|------------|
| ❌ `Minikube` не установлен | Выполните команды из подсказок `Install tips`, затем перезапустите `./scripts/setup-check.sh`. |
| ❌ Виртуализация выключена | Включите VT-x/AMD-V в BIOS/UEFI, перезагрузитесь, убедитесь командой `systeminfo | Select-String "Virtualization"`. |
| ⚠️ Недостаточно диска | Удалите старые образы: `minikube delete`, `docker system prune -af`, почистите загрузки. |
| ❌ Docker Desktop недоступен | Установите VirtualBox, запускайте Minikube с `--driver=virtualbox`. Скрипты автоматически будут использовать `minikube image build`. |
| ❌ Ошибка `certificate signed by unknown authority` | Проверьте дату и время на ноутбуке, затем перезапустите `minikube delete && minikube start`. |
| ⚠️ Веб-интерфейс не открывается по `ai-tourist.local` | Перепроверьте файл hosts, либо используйте `kubectl port-forward -n ai-tourist svc/ai-tourist-frontend 8080:80`. |
| ❌ Smoke-тесты не проходят | Посмотрите логи пода через `kubectl logs -n ai-tourist <имя-пода>` и повторите `make all`/`judge-run`. |

## 4. Дополнительные сценарии

### 4.1 Работа внутри виртуальной машины

Если корпоративная политика запрещает устанавливать Docker/VirtualBox напрямую, можно завести отдельную VM (например, VirtualBox + Ubuntu) и выполнить все шаги внутри неё:

1. Создайте виртуальную машину Ubuntu 22.04 с 6 CPU, 12 ГБ RAM и 40 ГБ диска.
2. Внутри VM установите зависимости из таблицы (колонка Ubuntu/Debian).
3. Скопируйте архив с проектом в VM (через Shared Folders или SCP).
4. Запустите `./scripts/judge-run.sh` внутри VM. Всё остальное работает так же, как на «живой» машине.

### 4.2 Перезапуск с нуля

1. `make clean` или команды удаления из раздела 2.6.
2. `minikube delete`
3. Запустите `judge-run` ещё раз — он сам пересоберёт образы и заново задеплоит сервисы.

## 5. Контакты

Если ни один из сценариев не помог, свяжитесь с командой разработки любым доступным способом. Укажите:

- операционную систему и версию;
- используемый драйвер Minikube (`docker`, `virtualbox`, `hyperv`, ...);
- полный вывод последней команды (скопируйте текст из терминала).

Это поможет быстро подсказать дальнейшие действия.

Удачной проверки! 🎉
