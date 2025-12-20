# 1. Basimage med Node
FROM node:20

# 2. Sätt arbetskatalog
WORKDIR /app

# 3. Kopiera package.json och package-lock.json
COPY package*.json ./

# 4. Rensa och installera om (för ARM64-kompatibilitet)
RUN rm -rf node_modules package-lock.json && npm install

# 5. Kopiera all frontend-kod
COPY . .

# 6. Exponera port för Vite dev-server
EXPOSE 5173

# 7. Starta Vite dev-server med Node-debug
CMD ["npm", "run", "dev", "--", "--host", "--port", "3000"]
