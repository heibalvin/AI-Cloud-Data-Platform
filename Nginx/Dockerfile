FROM nginx:1.31.7-alpine

LABEL org.opencontainers.image.title="aicd-nginx" \
      org.opencontainers.image.description="AICD Nginx chat frontend"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY Assets /usr/share/nginx/html/Assets

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
