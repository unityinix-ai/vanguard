# Deploy the Vanguard trio — all free, Render

Three services, three free Render web services, no card. The Dockerfiles are
all PORT-aware (Render injects `$PORT`).

**His-hand setup per service** (render.com → New → Web Service → connect the
public `unityinix-ai/vanguard` repo, Plan: **Free**):

| Service | Root Directory | Start note |
|---|---|---|
| **Gedo** | `gedo` | FastAPI. Health check path: `/health` if exposed, else `/`. |
| **Aurora** | `aurora` | FastAPI + WebSockets. Same health check approach. |
| **Hermes** | `hermes` | Go gRPC binary. Deploy as a **Private Service** (gRPC isn't HTTP) so Gedo/Aurora can reach it internally at `hermes:PORT`. Skip this one if you only want the public face — nothing customer-facing needs it yet. |

Render auto-detects each Dockerfile from the Root Directory. No environment
variables are required for any of the three (no secrets in these services).

**Sleep caveat:** free services sleep after ~15 min idle, 30–50s cold start.
The Paimon alarm cron now carries a silent warm-ping for every URL listed in
`~/workspace/product/aurora-license-server/deploy/warm-urls.txt` — add each
service's public URL there once deployed and they'll stay awake inside the
free 750 hrs/month allowance.

**Known limits:** Hermes (Go) was code-reviewed but never compiled here — no
Go toolchain on this machine. If its Render build fails, that's the first
place to look. Gedo's 19 tests and Aurora's 8 tests pass locally.
