# TDS Effective Configuration API

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/effective-config`.

## Deploy

Push this folder to a GitHub repository, then create a new Web Service on Render
from that repository. Render can use `render.yaml` as a Blueprint. Confirm the
environment variables `APP_WORKERS=9`, `APP_DEBUG=false`, and
`APP_API_KEY=key-izp9g7yq4a` are set in the service environment.

After deployment, submit:
`https://YOUR-RENDER-SERVICE.onrender.com/effective-config`

Test CLI overrides:
`https://YOUR-RENDER-SERVICE.onrender.com/effective-config?set=port=9000&set=debug=true`

`api_key` is always returned as `****`.
