# syntax=docker/dockerfile:1
# LEM2 reproduction image: federated Rough Set / LEM2 experiments (expanded 188 x 42 seeds,
# accelerated no-limit supplementary, 80/20 vs nested protocol comparison).
# Raw third-party data is NOT included; sources are downloaded at run time (network needed).
#
#   docker build -t lem2:20261128 \
#     --build-arg LEM2_REF=research/lem2-docker-20261128 \
#     --build-arg LEM2_EXPECT=<commit sha to assert, optional> \
#     -f docker/Dockerfile docker/
FROM python:3.12.3-slim-bookworm

ARG LEM2_REPO=https://github.com/Jimmy0307/LEM2.git
ARG LEM2_REF=research/lem2-docker-20261128
ARG LEM2_EXPECT=""

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 \
    LEM2_REPO_DIR=/opt/lem2 LEM2_WORK=/work HOME=/work/.home

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Sparse, shallow checkout of exactly the code the experiments import plus the two registry CSVs
# (the 300 MB docs/ tree and committed result data are not needed to run).
WORKDIR /opt
RUN git clone --filter=blob:none --no-checkout --depth 1 --branch "${LEM2_REF}" "${LEM2_REPO}" lem2 \
 && cd lem2 \
 && git sparse-checkout set --no-cone \
      '/fedrs/' '/roughset/' '/experiments/' '/teacher_demo/' '/tests/' '/docker/' '/requirements*.txt' \
      '/docs/research/teacher_dashboard/data/TEACHER_DATASET_MASTER_20261114.csv' \
      '/docs/research/redesign_20261116/data/CONFIRMATORY_SOURCE_REGISTRY.csv' \
 && git checkout \
 && git config --system --add safe.directory /opt/lem2 \
 && git rev-parse HEAD > /opt/LEM2_COMMIT \
 && if [ -n "${LEM2_EXPECT}" ] && [ "$(cat /opt/LEM2_COMMIT)" != "${LEM2_EXPECT}" ]; then \
      echo "commit mismatch: got $(cat /opt/LEM2_COMMIT), expected ${LEM2_EXPECT}" >&2; exit 1; fi

RUN pip install --no-cache-dir -r /opt/lem2/docker/requirements-docker.txt \
 && python -c "import numpy, pandas, scipy, pyarrow; print('numpy', numpy.__version__, 'pandas', pandas.__version__)"

RUN install -m 0755 /opt/lem2/docker/lem2 /usr/local/bin/lem2 \
 && useradd -m -u 1000 lem2 \
 && mkdir -p /work && chown lem2:lem2 /work

USER lem2
WORKDIR /opt/lem2
VOLUME ["/work"]
ENTRYPOINT ["lem2"]
CMD ["help"]
