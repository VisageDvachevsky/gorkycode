FROM node:20-alpine as base

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

FROM base as development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

FROM base as builder
RUN npm run build

FROM nginx:alpine as production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]