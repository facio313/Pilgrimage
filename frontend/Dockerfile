FROM node:22-slim AS build

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

ARG VITE_KAKAO_JS_KEY
ARG VITE_API_BASE_URL=/api
ENV VITE_KAKAO_JS_KEY=${VITE_KAKAO_JS_KEY}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY . .
RUN npm run build

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
