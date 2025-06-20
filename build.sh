#!/usr/bin/env bash
# exit on error
set -o errexit

# Instala as dependências do projeto
pip install -r requirements.txt

# Roda o comando para juntar todos os arquivos estáticos no STATIC_ROOT
python manage.py collectstatic --no-input

# Aplica as migrações do banco de dados
python manage.py migrate