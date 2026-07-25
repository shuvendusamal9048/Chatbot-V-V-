# Stage 1: Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Accept Vite environment variables as build arguments
ARG VITE_API_BASE_URL
ARG VITE_WS_BASE_URL

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_WS_BASE_URL=${VITE_WS_BASE_URL}

# Copy package files and install dependencies
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Copy source code and build production assets
COPY . .
RUN npm run build

# Stage 2: Production Nginx stage
FROM nginx:alpine

# Remove default nginx config and copy custom config
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 8015
EXPOSE 8015

CMD ["nginx", "-g", "daemon off;"]
