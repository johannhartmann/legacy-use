<p align="center">
  <img src="https://framerusercontent.com/images/dITUuTk8cKrr6KBrjwv9142LXLw.png" width="120" alt="legacy-use logo" />
  <h3 align="center">🚀  Turn any legacy application into a modern REST API, powered by AI.</h3>
</p>

# Contributing to legacy-use

First off, thanks for taking the time to make legacy-use even better! ❤️

The best ways to get involved:

- Create and comment on [issues](https://github.com/legacy-use/legacy-use/issues)
- Open a pull request—big or small, we love them all.

We welcome contributions through GitHub pull requests. This document outlines our conventions regarding development workflow, commit message formatting, contact points, and other resources. Our goal is to simplify the process and ensure that your contributions are easily accepted.

## Project Structure

### Tech Stack

- [React](https://react.dev/)
- [Vite](https://vitejs.dev/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Docker](https://www.docker.com/)

### Terminology

- Target - A target is a machine that you want to automate. It can be any computer that you can access via remote access software.
- Session - A session is a hosted connection between the target and the server. It is used to run jobs on the target.
- API - An API is a pre-defined set of instructions on how to execute a job on the target. It can include multiple steps, parameters, cleanup steps, etc.
- Job - A job is a single execution of an API on the target and works exactly like a REST endpoint. One can forward the needed parameters to the job, and the job will execute the API on the target.
- Tools - Modular helpers that enable the agent to interact with the target and external systems.

### Architecture

- The first thing you'll touch is our React-based frontend. With it you can set up targets, create API endpoints, and inspect running or past jobs.
- Our FastAPI server powers the frontend and, more importantly, acts as the gateway between you and the machines you want to automate. Once a target is set up and a Session created, the server spins up a Docker container that hosts that session solely for the target.
- Flow of a call:
    - One sends a POST request to the /targets/{target_id}/jobs/ endpoint.
    - The server will then spin up a Docker container that hosts the session, creating and maintaining a connection to the target.
    - The server adds the job to the target-specific job queue and returns a job ID.
        - Once the job leaves the queue it runs asynchronously, navigating the target machine.
        - The agent will iteratively take screenshots of the target, walk through the steps of the API, and make use of the different tools available to it, in order to execute the specified API job.
    - After completion, the agent sends the results back to the server, written to the database and marked as successful.

### Repository Structure

- [app](./app)

- [server](./server)
    - Have a look at the [core.py](./server/core.py) file to get an overview of the flow of a call.
    - Have a look at the [sampling_loop.py](./server/computer_use/sampling_loop.py) file to get an overview of the agentic loop.

- [infra](./infra)

## Getting setup for development

### Prerequisites

Before starting development, ensure you have the following tools installed:

**Core Requirements:**
- **Docker** - All services run in containers ([Get Docker](https://www.docker.com/get-started/))
- **Node.js 20+** - Frontend development ([nodejs.org](https://nodejs.org/))
- **Python 3.12+** - Backend development ([python.org](https://www.python.org/))
- **uv** - Fast Python package manager ([Install guide](https://docs.astral.sh/uv/))

**For Kubernetes Development:**
- **kubectl** - Kubernetes CLI ([Install kubectl](https://kubernetes.io/docs/tasks/tools/#kubectl))
- **helm** - Kubernetes package manager ([Install helm](https://helm.sh/docs/intro/install/))
- **kind** - Kubernetes in Docker ([Install kind](https://kind.sigs.k8s.io/docs/user/quick-start/#installation))
- **tilt** - Development environment for Kubernetes ([Install tilt](https://docs.tilt.dev/install.html))

**Quick Install Commands:**
```bash
# macOS with Homebrew
brew install kubectl helm kind tilt-dev/tap/tilt

# Linux/WSL
# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kind
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
chmod +x ./kind && sudo mv ./kind /usr/local/bin/kind

# tilt
curl -fsSL https://github.com/tilt-dev/tilt/releases/download/v0.33.6/tilt.0.33.6.linux.x86_64.tar.gz | tar -xzv tilt && sudo mv tilt /usr/local/bin
```

Following the steps in the [README.md](./README.md) file will get you up and running with the project, but if you want to get more in depth, here are some tips:

### Quick Development Setup with Makefile

The project includes a comprehensive Makefile for common development tasks:

```bash
# Set up complete development environment
make dev-setup    # Creates Kind cluster with KubeVirt
make tilt         # Start Tilt for hot-reloading development

# Code quality
make format       # Format all Python code
make lint         # Run linting checks
make check        # Run all quality checks
make test         # Run tests

# See all available commands
make help
```

### Local development cheatsheet

#### Backend (FastAPI)

1. **Install [uv](https://github.com/astral-sh/uv)** – a super-fast drop-in replacement for `pip`/`virtualenv`.

   *macOS*
   ```bash
   brew install uv
   ```
   *Linux / WSL / other*
   ```bash
   curl -Ls https://astral.sh/uv/install.sh | sh
   ```

2. **Create & activate a virtual-environment** in the project root:
   ```bash
   cd legacy-use   # repo root
   uv venv              # creates .venv using the current Python
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. **Install Python dependencies** defined in `pyproject.toml`:
   ```bash
   uv pip install -r pyproject.toml        # core deps
   uv pip install --group dev -r pyproject.toml  # dev/test/lint extras
   uv run pre-commit instal   # install pre-commit
   ```

4. **Run the API with hot-reload**:
   ```bash
   uvicorn server.server:app --host 0.0.0.0 --port 8088 --reload
   ```
   Open http://localhost:8088/redoc to confirm everything is up.

#### Frontend (React + Vite)

1. **Install Node.js (≥20) or [Bun](https://bun.sh/):**
   ```bash
   # macOS example
   brew install node        # or: brew install bun
   ```

2. **Install JS dependencies:**
   ```bash
   npm install              # or: bun install
   ```

3. **Start the Vite dev server (hot-reload):**
   ```bash
   npm run dev              # or: bun run dev
   ```
   Visit http://localhost:5173 and start hacking!

## Contact us via Discord

We have a dedicated Discord server for contributors and users. You can join it [here](https://link.browser-use.com/discord).
