# V1-P6 web service (DEC-064). Public ingress behind shared-credential
# authentication (proxy.ts). No credential is baked into this image; Cloud Run
# supplies PAA_WEB_USERNAME / PAA_WEB_PASSWORD / PAA_API_BASE_URL at runtime.
FROM node:22-slim AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ .
RUN npm run build

FROM node:22-slim AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public

EXPOSE 8080
ENV PORT=8080
CMD ["node", "server.js"]
