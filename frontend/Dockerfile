FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --frozen-lockfile

# VITE_API_URL is baked into the JS bundle at build time by Vite.
# docker-compose sets this to /api (nginx proxies /api → backend).
# Standalone: docker build --build-arg VITE_API_URL=https://your-api.onrender.com
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN npm run build
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx","-g","daemon off;"]