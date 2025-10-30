# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY front/package.json front/package-lock.json ./
RUN npm ci
COPY front/ ./
ARG VITE_MAPBOX_ACCESS_TOKEN
ARG VITE_BACKEND_URL
ENV VITE_MAPBOX_ACCESS_TOKEN=$VITE_MAPBOX_ACCESS_TOKEN
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL
RUN npm run build

# Runtime stage
FROM node:20-alpine
WORKDIR /app
COPY front/package.json front/package-lock.json ./
RUN npm ci --omit=dev
COPY --from=build /app/build ./build
EXPOSE 3000
CMD ["npm","run","start","--","-H","0.0.0.0","-p","3000"]