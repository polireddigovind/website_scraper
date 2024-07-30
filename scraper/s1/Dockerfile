FROM node:18-alpine

WORKDIR /scrapper_frontend

COPY public/ /scrapper_frontend/public
COPY src/ /scrapper_frontend/src
COPY package.json /scrapper_frontend

RUN npm install

EXPOSE 3000

CMD ["npm", "start"]