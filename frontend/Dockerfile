# Estágio 1: compila o React (precisa do Node só pra isso, não pra rodar depois).
FROM node:20-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

# Estágio 2: só os arquivos estáticos gerados, servidos por um Nginx leve
# (a imagem final não carrega Node/npm/node_modules — só HTML/CSS/JS prontos).
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
