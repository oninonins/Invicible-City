FROM node:20-alpine

WORKDIR /app

# The node_modules will be managed via a volume for dev,
# but we add this for completeness.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]
