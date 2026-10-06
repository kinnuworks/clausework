# Live-demo image. Runs stage-4 exactly as the band built it, then loads demo data
# through the service's own reset endpoint. Nothing under stage-4/ is changed.
# Build from the repository root:  docker build -f demo/Dockerfile -t tablekeeper-demo .
FROM node:22-alpine
WORKDIR /app
COPY stage-4/package.json ./
COPY stage-4/src ./src
COPY stage-4/ui ./ui
COPY demo/seed.json demo/start.mjs /demo/
ENV NODE_ENV=production PORT=8080 UV_THREADPOOL_SIZE=8
EXPOSE 8080
USER node
CMD ["node", "/demo/start.mjs"]
