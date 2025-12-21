FROM node:20-alpine

WORKDIR /app

COPY package.json ./

# Install with all optional dependencies explicitly included
RUN npm install --legacy-peer-deps && \
    npm install -D @rollup/rollup-linux-arm64-musl

COPY . .

EXPOSE 3000
EXPOSE 5173

# Run Vite development server with HMR enabled
CMD ["npm", "run", "dev"]
