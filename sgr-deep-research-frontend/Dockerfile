FROM node:22.12-alpine AS node
WORKDIR /app

COPY package.json \
     package-lock.json \
     .dockerignore \
     eslint.config.ts \
     vite.config.ts \
     tsconfig.json \
     tsconfig.app.json \
     tsconfig.node.json \
     ./

# build frontend
RUN npm ci --ignore-scripts

COPY . .

# Set the ENV variables
ARG VITE_API_BASE_URL
ARG VITE_APP_ENV
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_APP_ENV=${VITE_APP_ENV}

RUN npm run build --ignore-scripts

FROM nginx:stable-alpine AS server

COPY nginx/default.conf /etc/nginx/conf.d/

COPY --from=node --chown=nginx /app/dist/ /usr/share/nginx/html/
