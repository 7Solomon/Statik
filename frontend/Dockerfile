# syntax=docker/dockerfile:1

FROM node:24-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm npm ci

COPY . .
RUN npm run build

# Runtime: Nginx serves the static files
FROM nginx:alpine AS runner

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]