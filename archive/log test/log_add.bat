@echo off
cd /d "C:\Users\Roomelt Needo\OneDrive - Kurmik AS\Dokumendid\AAA CHATGPT\chatgpt_analytics"
call .venv\Scripts\activate.bat

set MESSAGE=%*
if "%MESSAGE%"=="" (
    set /p MESSAGE=Sisesta logitekst: 
)

python log_tool.py add "%MESSAGE%"