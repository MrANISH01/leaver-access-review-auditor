# Deployment Guide: Leaver Access Review Auditor

This repository is pre-configured to support two deployment architectures:
1. **Option 1 (Recommended / Quickest)**: Deploy **both Frontend and Backend on Vercel** (Full-stack Serverless with Python API).
2. **Option 2 (Decoupled)**: Deploy **Frontend on Vercel** and **Backend on Render** (Persistent Web Service).

---

## Option 1: Deploy Both Frontend & Backend on Vercel (All-in-One)

With this setup, the entire application (React SPA + Flask API) runs on Vercel in a single project. The Flask backend runs serverlessly via [`api/index.py`](file:///api/index.py) and requests to `/api/v1/*` are automatically routed with zero CORS configuration required.

### Steps to Deploy on Vercel:

1. **Push your code to GitHub**:
   ```bash
   git add .
   git commit -m "Configure Vercel and Render deployment"
   git push origin main
   ```

2. **Import Project on Vercel**:
   - Go to [vercel.com/new](https://vercel.com/new).
   - Select your GitHub repository: `MrANISH01/leaver-access-review-auditor`.
   - **Framework Preset**: Leave as *Other* or *Vite* (root `vercel.json` will automatically configure build and rewrites).
   - **Root Directory**: `./` (Leave as root).

3. **Configure Environment Variables (Optional)**:
   The application will automatically use sensible defaults (`DEMO_MODE=1`, `/tmp/auditor.sqlite3`, `APPROVER_ACTORS=demo-approver,approver@acme.example`).
   If you wish to customize:
   | Variable | Value | Description |
   |---|---|---|
   | `DEMO_MODE` | `1` | Enables demo endpoints and mock controls |
   | `APPROVER_ACTORS` | `demo-approver,approver@acme.example` | Allowlisted approval identities |
   | `CONNECTOR` | `synthetic` | Synthetic SaaS accounts connector |
   | `HR_SOURCE` | `synthetic` | Synthetic HR roster source |

4. **Deploy**:
   - Click **Deploy**. Vercel will install dependencies, build the frontend into `frontend/dist`, and deploy the Python serverless function at `/api/v1/*`.

---

## Option 2: Deploy Frontend on Vercel + Backend on Render

This setup runs the Flask API as a long-running service on Render with persistent worker processes, while Vercel hosts the React client.

### Step 1: Deploy Backend to Render

1. Go to [dashboard.render.com](https://dashboard.render.com/).
2. Click **New +** -> **Blueprint** (or **Web Service**).
3. Connect your repository: `MrANISH01/leaver-access-review-auditor`.
4. Render will detect [`render.yaml`](file:///render.yaml):
   - **Runtime**: Python 3
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn -w 2 -b 0.0.0.0:$PORT "app:create_app()"`
5. Set environment variables on Render:
   - `DEMO_MODE`: `1`
   - `ALLOW_LAN_DEMO`: `1`
   - `APPROVER_ACTORS`: `demo-approver,approver@acme.example`
   - `FRONTEND_ORIGIN`: `https://<your-app-name>.vercel.app` (add your Vercel URL once created)
6. Click **Apply / Create Web Service**. Render will deploy your service and give you a public URL (e.g., `https://leaver-access-auditor-backend.onrender.com`).

### Step 2: Deploy Frontend to Vercel

1. Go to [vercel.com/new](https://vercel.com/new).
2. Select your repository: `MrANISH01/leaver-access-review-auditor`.
3. Set **Root Directory** to `frontend`.
4. Under **Environment Variables**, add:
   - `VITE_DATA_MODE`: `live`
   - `VITE_API_BASE_URL`: `https://<your-render-app>.onrender.com/api/v1`
5. Click **Deploy**.
6. Once deployed, copy your Vercel URL and paste it into the Render backend's `FRONTEND_ORIGIN` environment variable so CORS allows requests.

---

## Testing & Verifying the Deployment

Once deployed:
1. Open your Vercel app URL.
2. In the top navigation, ensure the role switcher is available (`Demo analyst` / `Demo approver`).
3. Navigate to **Findings**: Verify synthetic leaver findings are loaded.
4. Create a deprovisioning review request and switch role to **Demo approver** to test approval actions.
5. Check `/api/v1/health` on your backend to confirm database and connector statuses are `ok`.
