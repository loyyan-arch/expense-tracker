FROM nginx:stable-alpine

ARG VCS_REF=unknown
LABEL org.opencontainers.image.revision=$VCS_REF

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY dist/ /usr/share/nginx/html/

EXPOSE 80
