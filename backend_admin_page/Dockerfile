FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html

# SPA nginx config — proper try_files fallback so direct route access returns index.html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000
