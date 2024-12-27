# ----- STAGE 1: BUILD IMAGE -----
FROM alpine:latest AS build-stage

# ----- Labels for the GitHub Code Repo 
LABEL org.opencontainers.image.source "https://www.github.com/lillian-alicia/bme680-mqtt/"
LABEL org.opencontainers.image.description "A docker image based on alpine, which reads data from a Bosch BME680 sensor and transmits it over MQTT to homeassistant."

COPY build /build
WORKDIR /build

RUN apk update \
&& apk add --no-cache python3 py3-pip

RUN python3 -m venv /bme680-mqtt/.venv && \
source /bme680-mqtt/.venv/bin/activate &&\
pip install --no-cache-dir  -r requirements.txt

# ----- STAGE 2: FINAL IMAGE -----
# Move to a second image stage once build is complete - cutting down on final image size
FROM alpine:latest AS final-stage

RUN apk update \
&& apk add --no-cache python3 py3-pip

# Copy virtual environment from build stage
COPY --from=build-stage /bme680-mqtt /bme680-mqtt 
# Copy src files from workspace
COPY src /bme680-mqtt
WORKDIR /bme680-mqtt/

RUN chmod +x start.sh

CMD ["/bin/sh", "start.sh"]