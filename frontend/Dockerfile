FROM node:18-alpine

WORKDIR /app

# Install dependencies first (cached layer)
COPY package.json package-lock.json* ./
RUN npm install

# Copy configuration (changes less frequently)
COPY vite.config.js postcss.config.js* tailwind.config.js* ./

# Copy everything else (source code will be bind-mounted in dev)
COPY . .

EXPOSE 3000

# Health check for frontend dev server
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000 || exit 1

# Run dev server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
