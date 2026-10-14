# Windows: run CLI demo, make figures, open dashboard
.\.venv\Scripts\Activate.ps1
python -m demo.run_demo
python -m demo.make_figures
streamlit run app/dashboard.py
