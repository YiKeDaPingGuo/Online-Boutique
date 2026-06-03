# AIOps Agent

This service embeds the LangGraph AIOps agent into Online Boutique.

## Interfaces

- `GET /healthz`: liveness probe.
- `GET /readyz`: validates the configured YAML can be loaded.
- `GET /api/v1/capabilities`: lists reserved integration interfaces.
- `GET /api/v1/config`: returns the active default config.
- `POST /api/v1/preflight`: validates datasource connectivity.
- `POST /api/v1/diagnose`: runs one diagnosis cycle.
- `POST /api/v1/events`: reserved event ingestion endpoint for `oversee`, load tests, and future tools.

## Local Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ARK_API_KEY="your ark api key"
python service.py
```

Run a mock diagnosis:

```bash
curl -s http://localhost:8080/api/v1/diagnose \
  -H 'Content-Type: application/json' \
  -d '{"config_path":"config/ark_mock.yaml"}'
```

## Kubernetes Secret

Create the model key before enabling LLM summaries in-cluster:

```bash
kubectl create secret generic aiopsagent-ark \
  --from-literal=ARK_API_KEY="$ARK_API_KEY"
```
