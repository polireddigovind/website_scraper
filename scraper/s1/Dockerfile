FROM node:18-alpine

WORKDIR /scrapper_frontend

COPY public/ /scrapper_frontend/public
COPY src/ /scrapper_frontend/src
COPY package.json /scrapper_frontend
COPY package-lock.json /scrapper_frontend

RUN npm install
RUN npm install socket.io-client

EXPOSE 3000

CMD ["npm", "start"]
