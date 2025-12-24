FROM google/cloud-sdk:alpine

# Install PostgreSQL client
RUN apk add --no-cache postgresql-client

WORKDIR /app

COPY script.sh .
RUN chmod +x script.sh

CMD ["./script.sh"]

