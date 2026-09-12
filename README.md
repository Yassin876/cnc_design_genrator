# CAD Studio — Monorepo Architecture

This repository has been restructured into a monorepo architecture to support microservices deployment on Railway alongside the desktop frontend application.

## Directory Structure

```
cad_studio/
├── desktop_app/               # React / Vite / Electron / Desktop UI application
├── services/                  # Microservices backend components
│   ├── main_backend/          # FastAPI main backend (Auth, Projects, Supabase, Orchestration)
│   ├── ai_server_2d/          # FastAPI 2D AI server (routing, Image2CAD, Flux, HF space client)
│   ├── nesting_worker/        # FastAPI Nesting Worker (Background job processing for rectpack nesting)
│   ├── edit_server/           # FastAPI Edit Server (ezdxf & Gemini structured edits)
│   └── _legacy_core/          # Temporary raw core pipeline modules (unified_pipeline, gemini_service, ai_generator)
├── shared/
│   └── schemas/               # Shared Pydantic models & DTO schemas
└── README.md                  # Project overview and microservices architecture documentation
```

## Microservices Breakdown

1. **Main Backend (`services/main_backend/`)**: Primary API gateway for the desktop client, handling authentication, job tracking in Supabase, and internal service orchestration.
2. **2D AI Server (`services/ai_server_2d/`)**: Handles 2D DXF generation from images or text prompts. Routes CAD images to local Image2CAD engine and regular images to HuggingFace Space.
3. **Nesting Worker (`services/nesting_worker/`)**: Dedicated background processing worker for sheet nesting using `rectpack`.
4. **Edit Server (`services/edit_server/`)**: Applies DXF geometry edits using `ezdxf` and Gemini LLM text instructions.
