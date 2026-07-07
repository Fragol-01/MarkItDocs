# MarkItDocs — imagen CLI/headless (sin GUI).
# Convierte MD/HTML -> DOCX/PDF por línea de comandos dentro del contenedor.
#
#   docker build -t markitdocs .
#   docker run --rm -v "$PWD:/data" markitdocs python crear_documento.py /data/doc.md -o /data/doc.docx
#   docker run --rm -v "$PWD:/data" markitdocs python -m markitpdf.cli /data/doc.md -o /data/doc.pdf

FROM python:3.12-slim

# Chromium para renderizar PDF (apt instala sus dependencias) + fuentes decentes.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# La GUI (customtkinter/tkinterdnd2) no aplica en un contenedor headless.
RUN grep -viE 'customtkinter|tkinterdnd2' requirements.txt > requirements-cli.txt \
    && pip install --no-cache-dir -r requirements-cli.txt

COPY crear_documento.py .
COPY markitpdf/ markitpdf/

# /usr/bin/chromium está en los CANDIDATE_PATHS de markitpdf/browser.py
# (vía shutil.which). El flag --no-sandbox ya lo pasa converter.py.
VOLUME ["/data"]
CMD ["python", "crear_documento.py", "--help"]
