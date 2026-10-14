# Windows PowerShell setup:  .\scripts\setup.ps1
# If scripts are blocked:    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest -q
