# Build stage
FROM node:20-alpine AS build
WORKDIR /app

# Declare build arguments first
ARG VITE_MAPBOX_ACCESS_TOKEN
ARG VITE_BACKEND_URL

# Set environment variables from build args - keep VITE_ prefix for build time
ENV VITE_MAPBOX_ACCESS_TOKEN=$VITE_MAPBOX_ACCESS_TOKEN
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

# Install dependencies
COPY front/package.json front/package-lock.json ./
RUN npm ci

# Copy source code and build
COPY front/ ./
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build/client ./build
EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
