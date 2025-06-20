from django.shortcuts import render

def home(request):
    """
    Renderiza a página inicial da aplicação.
    """
    # O contexto é um dicionário para enviar dados para o template,
    # por enquanto, ele estará vazio.
    context = {}
    return render(request, 'core/index.html', context)