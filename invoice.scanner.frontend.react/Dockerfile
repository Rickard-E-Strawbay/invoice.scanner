# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app

COPY invoice.scanner.frontend.react/package*.json ./

# Install dependencies with legacy peer deps support
RUN npm install --legacy-peer-deps

COPY invoice.scanner.frontend.react . /app

# Build production bundle
RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built files from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY invoice.scanner.frontend.react/nginx.conf /etc/nginx/conf.d/default.conf

# Copy startup script that handles PORT environment variable
COPY invoice.scanner.frontend.react/start.sh /start.sh
RUN chmod +x /start.sh

# Health check (uses PORT env var)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:${PORT:-8080}/health || exit 1

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Run startup script which handles PORT environment variable
CMD ["/start.sh"]
