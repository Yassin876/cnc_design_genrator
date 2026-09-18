# Anti Design — CNC Design Generator

![Anti Design Banner](https://img.shields.io/badge/Anti%20Design-v2.5.0%20AI-indigo?style=for-the-badge)
![FastAPI Backend](https://img.shields.io/badge/FastAPI-v0.110.0-009688?style=for-the-badge&logo=fastapi)
![Electron Shell](https://img.shields.io/badge/Electron-v34.5.8-47848F?style=for-the-badge&logo=electron)
![React 18](https://img.shields.io/badge/React-v18.3.1-61DAFB?style=for-the-badge&logo=react)
![Paddle Billing](https://img.shields.io/badge/Paddle-v2%20Billing-22c55e?style=for-the-badge)

**Anti Design (CNC Design Generator)** is a professional desktop CAD engineering application that unifies **AI Parametric Generation**, **2D Blueprint / 3D Solid CAD Editing**, **Automated Nesting & Manufacturing Validation**, and **Paddle Subscription Billing**.

---

## Key Features

- **Professional CAD Desktop Interface**: Precision CAD workspace with inspection controls, viewcube, and custom unit precision (`mm`, `cm`, `m`, `inch`).
- **AI CAD Generation Pipeline**: Text-to-CAD and Image-to-CAD generation driven by Gemini, Flux Schnell, and OpenCASCADE / ezdxf backend engines.
- **Automated Nesting & Validation**: Industrial nesting algorithms and real-time manufacturing constraint validation.
- **Paddle Billing Integration**: End-to-end subscription management with Paddle.js checkout overlay, HMAC-SHA256 signature verification, and automated webhook lifecycle management.
- **Security & Reliability**: Granular Zustand state management, JWT session authorization, and idempotent event processing.

---

## Quick Start Guide

### Prerequisites
- **Node.js**: v18.0.0 or higher
- **Python**: v3.10 or higher
- **ngrok** (for local webhook testing)

---

### Running in Development Mode

#### 1. Setup Environment Configuration
Ensure `.env` exists in the project root with the necessary configuration:
```bash
cp .env.example .env
```

#### 2. Install Dependencies
```bash
# Install Node dependencies
npm install

# Setup Python virtual environment
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Launch Desktop Application (Electron + Frontend + Backend)
```powershell
# In PowerShell / Command Prompt:
.\start-desktop.cmd

# Or using npm:
npm run dev
```
# Run ngrok URL Public Link 
ngrok http --url=chargable-ashley-tychistic.ngrok-free.dev 8000

*Electron will automatically launch the React Vite frontend (`http://localhost:5173`) and connect to the backend services.*

---

## Paddle Billing & Webhooks Setup

### 1. Run ngrok with Custom Domain
To expose the local backend (`port 8000`) to Paddle Webhooks:
```powershell
ngrok http --url=chargable-ashley-tychistic.ngrok-free.dev 8000
```
*(Or standard tunnel: `ngrok http 8000`)*

### 2. Configure Webhook in Paddle Dashboard
1. Go to **Paddle Sandbox Dashboard** ➡️ **Developer Tools** ➡️ **Notifications (Webhooks)** ➡️ **New Destination**.
2. Set the Destination URL:
   ```text
   https://chargable-ashley-tychistic.ngrok-free.dev/api/v1/billing/paddle/webhook
   ```
3. Subscribe to events:
   - `subscription.created`
   - `subscription.activated`
   - `subscription.updated`
   - `subscription.canceled`
   - `subscription.past_due`
   - `transaction.paid`
   - `transaction.completed`
   - `transaction.payment_failed`
4. Copy the **Webhook Secret Key** into `.env`:
   ```ini
   PADDLE_WEBHOOK_SECRET_KEY=pdl_ntfset_your_secret_key_here
   ```

### 3. Paddle Price Identifiers
- **Pro ($10/mo)**: `pri_01m2p85k69p7fxaa2aam45r4jw`
- **Pro Plus ($25/mo)**: `pri_01m2p89n5cce3wjzk8y1aerbg1`
- **Business**: `pri_01m2p8cbbevbzyvxgp5pfsg746`

---

## Testing & Verification

### Test Public Paddle Configuration via PowerShell
```powershell
Invoke-RestMethod -Uri "https://chargable-ashley-tychistic.ngrok-free.dev/api/v1/billing/paddle/config" -Method GET
```

### Run Automated Tests
```powershell
# TypeScript Compilation Check
npx tsc --noEmit

# Paddle Billing & Webhook Test Suite
.venv\Scripts\python.exe tests/test_paddle_billing.py

# Frontend Tests
npm test
```

---

## Project Structure

```
cnc_design_genrator/
├── backend/                  # FastAPI Backend API Service
│   ├── app/
│   │   ├── api/              # Domain Routers (auth, billing, projects, etc.)
│   │   ├── core/             # Security, Logging, Config, Database
│   │   ├── models/           # SQLAlchemy Models (User, PaddleWebhookEvent, etc.)
│   │   ├── schemas/          # Pydantic Request/Response Schemas
│   │   └── services/         # Business Logic (PaddleService, SubscriptionService)
├── core/                     # CAD & AI Engine (ezdxf, nesting, pipeline)
├── electron/                 # Desktop Shell Main & Preload Scripts
├── src/                      # React 18 Frontend UI
│   ├── app/store/            # Granular Zustand Stores (Billing, Auth, Workspace)
│   ├── components/           # UI Components & Dialog Modals
│   ├── features/             # Feature Modules (3D Viewport, 2D Canvas, Settings, etc.)
│   ├── services/             # API Clients & Paddle.js Service
│   └── types/                # TypeScript Interfaces & API Contracts
├── tests/                    # Pytest & Vitest Suites
├── start-desktop.cmd         # One-click desktop launcher
└── .env                      # Environment Variables
```

---

## License
Confidential & Proprietary — Anti Design.
