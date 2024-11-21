FROM python:3.11-slim

WORKDIR /app

# COPY match-reports /app/match-reports
COPY requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "match-reports/existing-match-reports-code/app.py"]
