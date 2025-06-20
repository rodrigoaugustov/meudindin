#!/bin/sh

# O shell irá encerrar o script imediatamente se um comando falhar
set -e

# Executa as migrações do banco de dados do Django
echo "Executando migrações do banco de dados..."
python manage.py migrate --no-input

# Inicia o servidor Gunicorn
echo "Iniciando o servidor Gunicorn..."
exec gunicorn --bind 0.0.0.0:8080 --workers 2 gestor_financeiro.wsgi:application