@echo off
setlocal
cd /d %~dp0
if not exist venv\Scripts\python.exe (
  echo Creating virtual environment...
  py -m venv venv
)
call venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python manage.py migrate
python seed_demo.py
python manage.py check
python manage.py runserver
