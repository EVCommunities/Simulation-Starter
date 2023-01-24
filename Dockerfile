FROM python:3.10.9-slim
LABEL org.opencontainers.image.source https://github.com/EVCommunities/Simulation-Starter
LABEL org.opencontainers.image.description "Docker image for the simulation starter for EVCommunities demo."

WORKDIR /app
RUN mkdir -p /app/manifests
RUN mkdir -p /app/simulations

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY example_parameters.json /app/example_parameters.json
COPY demo/ /app/demo/

CMD [ "python3", "-u", "-m", "demo.demo" ]
