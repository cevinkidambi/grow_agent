# Cloud Run Deployment & Frontend Implementation Plan

This guide outlines how to containerize and deploy the Grow Agent backend to Google Cloud Run and a recommended approach for delivering the requested frontend experience.

## 1) Prerequisites
- Google Cloud project with billing enabled.
- `gcloud` CLI installed and initialized (`gcloud init`).
- Artifact Registry repository (e.g., `asia-docker.pkg.dev/<PROJECT_ID>/grow-agent-repo`).
- Service account for Cloud Run with permissions: `roles/run.admin`, `roles/iam.serviceAccountUser`, `roles/artifactregistry.writer`, and access to Secret Manager/Cloud SQL if used.
- `.env` file (not committed) holding keys like `GOOGLE_API_KEY` for Gemini/ADK, plus any POS or OAuth secrets.

## 2) Containerization
1. Create a `Dockerfile` in the repo root:
    ```dockerfile
    # Use a slim Python base
    FROM python:3.11-slim

    # System deps (add build-essential if you need to compile packages)
    RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates && rm -rf /var/lib/apt/lists/*

    WORKDIR /app

    # Install Python deps first for better caching
    COPY backend/requirements.txt ./requirements.txt
    RUN pip install --no-cache-dir -r requirements.txt

    # Copy source
    COPY backend/ ./backend/

    # Expose the port FastAPI/Uvicorn will listen on
    EXPOSE 8080

    # Set the entrypoint; adjust the module if you name your app differently
    CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
    ```
2. Ensure your FastAPI app lives at `backend/main.py` and exposes `app = FastAPI()` with routes for health checks and the chat endpoint that invokes `root_agent`.
3. Keep secrets out of the image; rely on environment variables or Secret Manager.

## 3) Build & Push
From the repo root:
```bash
PROJECT_ID=<your-project-id>
REGION=<your-region>            # e.g., asia-southeast2
REPO=grow-agent-repo
IMAGE=cloud-run-backend
TAG=v1

# Configure Docker to use Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:${TAG}
```

## 4) Deploy to Cloud Run
```bash
SERVICE=grow-agent-api
DB_CONN_NAME=<if-using-cloud-sql> # optional
POS_CALLBACK=https://<your-pos-app>/oauth/callback
GOOGLE_CLIENT_ID=<oauth-client-id>
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_API_KEY=<gemini-or-adk-key>

# Deploy
gcloud run deploy ${SERVICE} \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${IMAGE}:${TAG} \
  --region ${REGION} \
  --platform managed \
  --allow-unauthenticated \  # tighten later behind IAP or Auth proxy
  --port 8080 \
  --set-env-vars GOOGLE_API_KEY=${GOOGLE_API_KEY},POS_CALLBACK=${POS_CALLBACK},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID} \
  --set-secrets GOOGLE_CLIENT_SECRET=projects/<PROJECT_NUM>/secrets/GOOGLE_CLIENT_SECRET:latest \  # optional Secret Manager usage
  --cpu 1 --memory 1Gi
```
Adjust flags for VPC connectors, Cloud SQL (`--add-cloudsql-instances`), or minimum instances (`--min-instances`) based on latency needs.

## 5) Frontend Plan (Landing → Auth → Risk Profiling → Dashboard → Advisor → Partner Redirect)
### Stack Recommendation
- **Next.js (App Router) + TypeScript** hosted on **Cloud Run** or **Firebase Hosting** (static export). Use **Material UI/Tailwind** for rapid UI work.
- **Authentication**: Google OAuth via `next-auth` (Google provider) and a custom provider for GetU.Pos SSO (use OAuth/OIDC or JWT SSO issued by POS). Store sessions in `@auth/core` JWTs or a managed store (e.g., Firestore) if sharing across services.

### Page/Route Outline
1. **Landing (`/`)**: Product overview, feature cards (risk profiling, personalized funds, channel partners, Gemini-powered advisor), CTA buttons (“Get Started”, “Login with Google”, “Login with GetU.Pos”).
2. **Auth (`/auth/login`)**: Buttons for Google and GetU.Pos SSO; include email/password fallback. After login, redirect to `/risk-profile` if missing, else `/dashboard`.
3. **Register (`/auth/register`)**: Standard form + Google SSO + GetU.Pos account-link flow (call POS auth endpoint; store resulting token/claims in your backend).
4. **Risk Profiling (`/risk-profile`)**: Short questionnaire (horizon, drawdown tolerance, investment goal). POST answers to backend; persist `risk_profile` via the `manage_user_profile` tool or your user store. Show allowed fund categories per profile.
5. **Dashboard (`/dashboard`)**: 
   - Summary card of detected risk profile and allowed fund types.
   - Sections for each fund type with recommended funds (call backend `/funds?type=...`).
   - Channel partner carousel (Bibit, Bareksa, Banks) with promos retrieved from backend `get_partner_info`.
   - Visualization widget fed by `get_visualization_data` (Top 10% vs Rest or Head-to-Head).
6. **Advisor Chat (`/advisor`)**: Chat UI that streams responses from backend `/chat` endpoint tied to `root_agent`; include quick prompts (e.g., “Explain why this fund fits my profile”).
7. **Invest CTA**: For each fund card, “Invest via <Partner>” button linking to the partner portal/referral URL; open in new tab and log the click.

### Frontend→Backend Contracts (suggested)
- `POST /chat { message, sessionId }` → streamed/JSON reply from `root_agent` (mirrors user language, applies risk gates).
- `GET /funds?type=PU|PT|CP|SH` → list from `get_top_funds` with scores/ranks.
- `GET /funds/{name}` → details from `get_fund_analysis`.
- `GET /partners?name=Bibit|Bareksa|Bank|ALL` → promos/benefits.
- `POST /risk-profile { answers }` → stores profile via `manage_user_profile` + your DB/session store.

### UX/Implementation Notes
- Store auth tokens in HTTP-only cookies; include CSRF protection for POSTs.
- Use incremental static regeneration for landing content; keep authed flows server-side rendered or protected routes.
- Add loading/error states around data fetches; surface OOS reliability/alpha alongside fund scores to match the agent’s messaging.
- Instrument events (login method, profile completion, advisor chats, partner clicks) to Google Analytics or BigQuery via GTM.

## 6) Observability & Ops
- Enable Cloud Logging/Monitoring; add `/healthz` endpoint for probes.
- Set Cloud Run concurrency based on expected traffic (default 80; reduce if CPU-bound during model calls).
- If using Cloud SQL, prefer SQL Auth proxy sidecar or `--add-cloudsql-instances` and set `DB_SOCKET_DIR=/cloudsql`.
- Consider a Cloud CDN + HTTPS load balancer fronting the frontend, and Cloud Armor for basic security policies.

## 7) Local Development
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8080
# Frontend: npm install && npm run dev (if using Next.js)
```

Use a `.env` file for local secrets; mirror the same names in Cloud Run `--set-env-vars` for consistency.
