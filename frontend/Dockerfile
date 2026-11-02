FROM nginx:stable-alpine

ENV URL_SERVICE_HOST=url-service \
    URL_SERVICE_PORT=8000 \
    DNS_RESOLVER=127.0.0.11 \
    NGINX_ENVSUBST_FILTER="^(URL_SERVICE_HOST|URL_SERVICE_PORT|DNS_RESOLVER)$"

COPY index.html styles.css app.js /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/templates/default.conf.template

EXPOSE 80
