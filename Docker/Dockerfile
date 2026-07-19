# PyTorch 2.7 + CUDA 12.8 + cuDNN 9, runtime variant (no compiler toolchain → much smaller image).
# Pairs with `deploy.resources.reservations.devices` / `runtime: nvidia` in docker-compose.yml.
# GPU access still requires the NVIDIA Container Toolkit on the host.
FROM pytorch/pytorch:2.7.0-cuda12.8-cudnn9-runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/workspace \
    MODEL_DIR=/workspace/models \
    # Make sure transformers/datasets can find CUDA at runtime.
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /workspace

# System deps kept minimal. The -runtime image already ships the libraries
# needed to run, so build-essential is intentionally dropped to keep the
# image small. Re-add it only if a future dependency must compile from source.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl wget libatomic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# We can't check torch.cuda.is_available() during build because Docker builds
# do not have access to the GPU by default. We just print the compiled CUDA version.
RUN python -c "import torch; print('PyTorch compiled with CUDA:', torch.version.cuda)"

COPY . .

EXPOSE 8501
EXPOSE 8000

# Default entry point stays the Streamlit demo. Training runs on demand via
# `docker compose run phishing-detector python -m src.models.train_roberta ...`.
CMD ["streamlit", "run", "frontend/streamlit_app.py", "--server.address=0.0.0.0"]
