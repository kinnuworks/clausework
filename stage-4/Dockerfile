FROM node:22-alpine
WORKDIR /app
COPY package.json ./
COPY src ./src
COPY ui ./ui
ENV NODE_ENV=production PORT=8080 UV_THREADPOOL_SIZE=8
EXPOSE 8080
USER node
CMD ["node", "src/server.js"]
