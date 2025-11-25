# OSRM Dockerfile with embedded Montreal data

# FROM --platform=linux/arm64 osrm/osrm-backend:latest
FROM ghcr.io/project-osrm/osrm-backend:v6.0.0@sha256:733da1be48587358a417750655cc4748bbae9af60e3ace610db68d4febe038d8

# Copy the pre-processed OSRM data into the container
# (assumes osrm-extract, osrm-partition, and osrm-customize have already been run on montreal.osm.pbf locally)
COPY osrm-data /data

# Expose OSRM default port
EXPOSE 5000

# Run OSRM routing server with Montreal data
CMD ["osrm-routed", "--algorithm", "mld", "/data/montreal.osrm"]
