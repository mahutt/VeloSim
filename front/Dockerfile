# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Declare build arguments first
ARG VITE_MAPBOX_ACCESS_TOKEN
ARG VITE_BACKEND_URL

# Set environment variables from build args
ENV VITE_MAPBOX_ACCESS_TOKEN=$VITE_MAPBOX_ACCESS_TOKEN
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

# Install dependencies
COPY front/package.json front/package-lock.json ./
RUN npm ci

# Copy source code and build
COPY front/ ./
RUN npm run build

# Runtime stage - Use nginx to serve static files
FROM nginx:alpine

# Remove default nginx config and copy our SPA configuration
RUN rm /etc/nginx/conf.d/default.conf
COPY front/nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built SPA from build stage
COPY --from=build /app/build/client /usr/share/nginx/html
