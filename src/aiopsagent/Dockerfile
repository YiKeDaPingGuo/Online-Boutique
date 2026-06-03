FROM python:3.12.6-slim@sha256:ad48727987b259854d52241fac3bc633574364867b8e20aec305e6e7f4028b26 AS base

FROM base AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --prefix=/install -r requirements.txt

FROM base
ENV PYTHONUNBUFFERED=1
ENV AIOPS_CONFIG=config/online_boutique.yaml
ENV PORT=8080

WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

EXPOSE 8080
ENTRYPOINT ["python", "service.py"]
