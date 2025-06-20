# 1. Use uma imagem base oficial do Python
FROM python:3.11-slim

# Defina o diretório de trabalho
WORKDIR /app

# Copie o arquivo de dependências
COPY requirements.txt .

# Instale as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copie o código da aplicação
COPY . .

# Dê permissão de execução ao script de entrypoint
RUN chmod +x /app/entrypoint.sh

# Defina o script de entrypoint como o comando de inicialização do container
ENTRYPOINT ["/app/entrypoint.sh"]