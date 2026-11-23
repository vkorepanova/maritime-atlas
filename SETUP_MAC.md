# Развёртывание на MacBook и загрузка в GitHub

## A. Локальная подготовка

1. Скачайте архив `maritime-atlas.zip`, распакуйте в папку **Загрузки**. Убедитесь, что внутри есть `README.md`, `docs` и `src`.
2. Откройте **Терминал** на MacBook и выполните команды:

```bash
cd ~/Downloads/maritime-atlas
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
maritime-atlas serve
```

3. Откройте в браузере http://127.0.0.1:8020. Включите вкладку **Грузопотоки**. На ней отображается геометрия 15 маршрутов без вымышленных масс. Остальные две карты станут содержательными после подключения данных.
4. Для AIS используйте другое окно Терминала, в нём снова выполните `cd ~/Downloads/maritime-atlas` и `source .venv/bin/activate`, создайте `.env` и запустите команду `maritime-atlas track` из README.

## B. Создание нового репозитория через сайт GitHub

1. Войдите в свой аккаунт на [github.com](https://github.com/).
2. Нажмите знак **+** → **New repository**.
3. Введите **maritime-atlas** и выберите **Public**, если хотите бесплатно публиковать веб-карту на GitHub Pages.
4. **Не ставьте** галочки `Add a README file`, `.gitignore` и `Choose a license` - они уже находятся в архиве.
5. Нажмите **Create repository**. Скопируйте адрес вида `https://github.com/ВАШ_ЛОГИН/maritime-atlas.git`.

В новом окне Терминала из папки проекта:

```bash
cd ~/Downloads/maritime-atlas
git init
git branch -M main
git add .
git commit -m "Initial maritime atlas"
git remote add origin https://github.com/ВАШ_ЛОГИН/maritime-atlas.git
git push -u origin main
```

Замените `ВАШ_ЛОГИН` на свой GitHub username. Важно: при работе по HTTPS GitHub не принимает обычный пароль аккаунта как пароль Git. Удобнее поставить GitHub CLI и войти через браузер:

```bash
brew install gh
gh auth login
```

При установке выберите `GitHub.com` → `HTTPS` → `Login with a web browser`. Если Homebrew отсутствует, используйте официальную инструкцию [GitHub CLI](https://cli.github.com/) или GitHub Desktop. Можно сначала авторизоваться через `gh`, затем выполнить команды `git push`.

**Второй способ без Git из Терминала:** откройте папку проекта через [GitHub Desktop](https://desktop.github.com/), выберите `Add local repository` → `Create repository here`, затем `Publish repository`. Для публичной карты снимите `Keep this code private`.

## C. Публикация веб-карты на GitHub Pages

1. Откройте новый репозиторий на GitHub.
2. Нажмите **Settings** → **Pages**.
3. В разделе **Build and deployment** установите `Source: Deploy from a branch`.
4. Выберите `Branch: main`, `Folder: /docs` и нажмите **Save**.
5. Адрес карты появится в том же разделе, обычно `https://ВАШ_ЛОГИН.github.io/maritime-atlas/`.

Публикуется только папка `docs` и её статические данные. Локальные ключи `.env`, каталог `runtime` и служба FastAPI не выполняются на GitHub Pages. **Живой AIS будет работать на локальной карте при работающем приёмнике, но не на публичном GitHub Pages без собственного бэкенда.**

После первого развёртывания укажите настоящий URL в `docs/index.html` в элементах `canonical` и `og:url` для поисковых систем.

## D. Подключение того же репозитория из Jupyter

1. Откройте `notebooks/01_connect_from_github.ipynb`.
2. Измените `GITHUB_USER = "YOUR_GITHUB_USERNAME"` на свой GitHub username.
3. Последовательно выполните ячейки. Ноутбук загрузит GeoJSON с `raw.githubusercontent.com`, сформирует таблицу и откроет опубликованную карту.
4. Для Python-модулей из репозитория при необходимости выполните в Jupyter:

```python
import sys
!{sys.executable} -m pip install git+https://github.com/ВАШ_ЛОГИН/maritime-atlas.git
```

## E. Как публиковать обновления

```bash
cd ~/Downloads/maritime-atlas
git add docs data src notebooks README.md
git commit -m "Update maritime layers"
git push
```

Команда `git add` исключает личный `.env` и локальные AIS-файлы `runtime` благодаря `.gitignore`. Перед каждым коммитом можно выполнить `git status` и убедиться, что ключи и закрытые данные не попадут в публичный репозиторий.
