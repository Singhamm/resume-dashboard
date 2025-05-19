# Resume Dashboard Demo (Streamlit)

This is a fully local demo of the resume formatting flow, using FastAPI and Streamlit.

## Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start API
uvicorn app.main:app --reload

# In another terminal, start UI
streamlit run streamlit_app.py