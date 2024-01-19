docker run -d --name pgsql \
   -e POSTGRES_PASSWORD=hello.c \
   -e POSTGRES_USER=pgadmin \
   -p 5432:5432 \
   postgres 
