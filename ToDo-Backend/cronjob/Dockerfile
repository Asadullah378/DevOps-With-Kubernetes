FROM curlimages/curl:latest

WORKDIR /usr/src/app

COPY script.sh .

USER root
RUN chmod +x script.sh

USER curl_user

CMD ["./script.sh"]

