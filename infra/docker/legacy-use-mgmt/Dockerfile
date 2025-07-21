FROM docker.io/ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV DEBIAN_PRIORITY=high

RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get -y install \
    # requirements for docker-ce repo
    ca-certificates \
    curl \
    gnupg \
    python3 \
    gunicorn \
    # Database reqs
    sqlite3 \
    sudo \
    # PPA req
    software-properties-common && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js (manual setup)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs

# Docker CLI will be installed after user creation





# setup user
ENV USERNAME=legacy-use-mgmt
ENV HOME=/home/$USERNAME
RUN useradd -m -s /bin/bash -d $HOME $USERNAME

# Install Docker CLI first
RUN install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | tee /etc/apt/keyrings/docker.asc > /dev/null  && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null  && \
    apt update && \
    apt install -y docker-ce-cli

# Create docker group and add user to both docker groups
RUN groupadd -g 141 docker-host && \
    usermod -aG docker-host $USERNAME
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
USER legacy-use-mgmt
WORKDIR $HOME

# Copy and install Python requirements with uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY --chown=$USERNAME:$USERNAME pyproject.toml uv.lock $HOME/
RUN uv sync --locked

# setup desktop env & app
COPY --chown=$USERNAME:$USERNAME infra/docker/legacy-use-mgmt/image/ $HOME/
COPY --chown=$USERNAME:$USERNAME server/ $HOME/server/
COPY --chown=$USERNAME:$USERNAME app/ $HOME/app/
# Copy frontend configuration files
COPY --chown=$USERNAME:$USERNAME package*.json $HOME/
COPY --chown=$USERNAME:$USERNAME index.html vite.config.js $HOME/
COPY --chown=$USERNAME:$USERNAME public/ $HOME/public/

# install npm dependencies
RUN npm install

ENTRYPOINT [ "./entrypoint.sh" ]
