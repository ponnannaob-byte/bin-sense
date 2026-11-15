@echo off
call venv\Scripts\activate
streamlit run app.py --theme.base light --theme.primaryColor "#00B37E" --theme.backgroundColor "#FFFFFF" --theme.secondaryBackgroundColor "#FFFFFF" --theme.textColor "#0E1F2F"
