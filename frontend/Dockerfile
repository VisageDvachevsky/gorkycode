FROM node:20-alpine AS base
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci

FROM base AS builder
COPY frontend/ .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
