FROM registry.access.redhat.com/ubi9/python-312:latest

USER root

RUN groupadd -r sandbox && useradd -r -g sandbox -d /sandbox sandbox

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY agent.py /app/agent.py
COPY config.py /app/config.py
COPY state.py /app/state.py
COPY lib/ /app/lib/

RUN mkdir -p /sandbox && chown sandbox:sandbox /sandbox

USER sandbox
WORKDIR /app

ENTRYPOINT ["python3", "agent.py"]
