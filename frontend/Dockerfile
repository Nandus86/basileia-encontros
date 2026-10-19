FROM node:20-alpine AS builder
WORKDIR /app
RUN apk add --no-cache libc6-compat
COPY package.json package-lock.json ./
RUN npm ci

# O endereço da API fica gravado no app durante o build
ARG NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN case "$NEXT_PUBLIC_API_BASE" in http://?*|https://?*) ;; \
      *) echo "ERRO: NEXT_PUBLIC_API_BASE precisa ser o endereço da API (ex.: https://encontros-api.basileia.global). Veio: '$NEXT_PUBLIC_API_BASE'"; exit 1;; esac

COPY . .
RUN npm run build

# Imagem final leve: só o servidor "standalone" do Next
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
