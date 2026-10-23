import asyncio
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001").rstrip("/")
STUDENT_SERVICE_URL = os.getenv("STUDENT_SERVICE_URL", "http://localhost:8002").rstrip("/")
COURSE_SERVICE_URL = os.getenv("COURSE_SERVICE_URL", "http://localhost:8003").rstrip("/")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))

# First path segment -> (service name, base URL)
ROUTES = {
    "auth": ("auth-service", AUTH_SERVICE_URL),
    "students": ("student-service", STUDENT_SERVICE_URL),
    "courses": ("course-service", COURSE_SERVICE_URL),
}

HOP_BY_HOP = {"connection", "keep-alive", "transfer-encoding", "te", "trailer", "upgrade", "content-length", "content-encoding"}

app = FastAPI(
    title="API Gateway",
    version="1.0.0",
    description=(
        "Single entry point for the frontend. Routes /auth/*, /students/* and /courses/* to the "
        "matching microservice. See each service's own /docs for the full Swagger documentation."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["gateway"])
def root():
    return {"service": "api-gateway", "routes": {f"/{prefix}/*": name for prefix, (name, _) in ROUTES.items()}}


@app.get("/health", tags=["gateway"])
async def health():
    """Reports the status of the gateway and every downstream service."""

    async def check(name: str, url: str):
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                r = await client.get(f"{url}/health")
            return name, "ok" if r.status_code == 200 else f"error ({r.status_code})"
        except httpx.HTTPError:
            return name, "unreachable"

    results = await asyncio.gather(*(check(name, url) for name, url in ROUTES.values()))
    services = dict(results)
    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return {"service": "api-gateway", "status": overall, "services": services}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
async def proxy(path: str, request: Request):
    prefix = path.split("/", 1)[0]
    route = ROUTES.get(prefix)
    if route is None:
        return JSONResponse(status_code=404, content={"detail": f"Route '/{path}' not found"})

    service_name, base_url = route
    url = f"{base_url}/{path}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() in {"authorization", "content-type", "accept"}
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            upstream = await client.request(
                request.method,
                url,
                params=request.query_params,
                content=body,
                headers=headers,
            )
    except httpx.ConnectError:
        return JSONResponse(status_code=503, content={"detail": f"{service_name} is unavailable"})
    except httpx.TimeoutException:
        return JSONResponse(status_code=504, content={"detail": f"{service_name} timed out"})
    except httpx.HTTPError:
        return JSONResponse(status_code=502, content={"detail": f"Bad response from {service_name}"})

    response_headers = {k: v for k, v in upstream.headers.items() if k.lower() not in HOP_BY_HOP}
    response_headers.pop("content-type", None)
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )
