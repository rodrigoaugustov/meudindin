# core/forms.py

from django import forms
from django.db.models import Q

from .models import Lancamento, Categoria, ContaBancaria, CartaoCredito

class ContaBancariaForm(forms.ModelForm):
    class Meta:
        model = ContaBancaria
        fields = ['nome_banco', 'agencia', 'numero_conta', 'saldo_inicial', 'data_saldo_inicial']
        # Você pode personalizar os labels aqui se quiser
        labels = {
            'nome_banco': 'Nome do Banco',
            'numero_conta': 'Número da Conta',
            'saldo_inicial': 'Saldo Inicial (R$)',
            'data_saldo_inicial': 'Data Saldo Inicial',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Classes CSS padrão para os campos do formulário
        tailwind_classes = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"

        # Itera sobre todos os campos do formulário e adiciona as classes
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = tailwind_classes
            
            # Adiciona placeholders para uma melhor UX
            if field_name == 'agencia':
                field.widget.attrs['placeholder'] = '0001 (Opcional)'
            if field_name == 'numero_conta':
                field.widget.attrs['placeholder'] = '12345-6'
            if field_name == 'saldo_inicial':
                field.widget.attrs['placeholder'] = '0,00'
            if field_name == 'data_saldo_inicial':
                field.widget.attrs['type'] = 'date'

class CartaoCreditoForm(forms.ModelForm):
    class Meta:
        model = CartaoCredito
        fields = ['nome_cartao', 'limite', 'dia_fechamento', 'dia_vencimento']
        labels = {
            'nome_cartao': 'Nome do Cartão (Apelido)',
            'limite': 'Limite do Cartão (R$)',
            'dia_fechamento': 'Dia do Fechamento da Fatura',
            'dia_vencimento': 'Dia do Vencimento da Fatura',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tailwind_classes = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = tailwind_classes

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        labels = {'nome': 'Nome da Categoria'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs['class'] = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        self.fields['nome'].widget.attrs['placeholder'] = 'Ex: Alimentação, Moradia, Lazer...'


class CategoriaModelChoiceField(forms.ModelChoiceField):
    """Campo customizado para exibir apenas o nome da categoria no dropdown."""
    def label_from_instance(self, obj):
        return obj.nome

class LancamentoForm(forms.ModelForm):
    # Usando o campo customizado para as categorias
    categoria = CategoriaModelChoiceField(
        queryset=Categoria.objects.none(), # O queryset será definido no __init__
        required=False
    )
    
    data_caixa = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        required=False,
        label="Data de Pagamento (Caixa)"
    )

    conciliar_automaticamente = forms.BooleanField(
        required=False,
        initial=False,
        label="Marcar como conciliado",
        help_text="Marque esta opção se o lançamento já estiver confirmado em seu extrato."
    )

    class Meta:
        model = Lancamento
        fields = [
            'descricao', 'valor', 'tipo', 'data_competencia', 'data_caixa',
            'categoria', 'conta_bancaria', 'cartao_credito'
        ]
        widgets = {
            'data_competencia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex: Compra no supermercado'}),
            'valor': forms.NumberInput(attrs={'placeholder': '150,75'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            # Filtra os querysets dos campos ForeignKey
            self.fields['categoria'].queryset = Categoria.objects.filter(
                Q(usuario=user) | Q(usuario__isnull=True)
            ).order_by('nome')
            self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(usuario=user)
            self.fields['cartao_credito'].queryset = CartaoCredito.objects.filter(usuario=user)
        
        # Adiciona classes do Tailwind
        tailwind_classes = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        for field_name, field in self.fields.items():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = tailwind_classes
    
    def clean(self):
        """
        Validação customizada para garantir que conta bancária e cartão de crédito
        sejam mutuamente exclusivos.
        """
        cleaned_data = super().clean()
        conta_bancaria = cleaned_data.get("conta_bancaria")
        cartao_credito = cleaned_data.get("cartao_credito")

        if conta_bancaria and cartao_credito:
            # Se ambos os campos foram preenchidos, levanta um erro de validação
            raise forms.ValidationError(
                "Um lançamento não pode ser associado a uma conta e a um cartão de crédito ao mesmo tempo. Por favor, escolha apenas um."
            )
        
        if not conta_bancaria and not cartao_credito:
            # Garante que pelo menos um dos dois seja preenchido
            raise forms.ValidationError(
                "Um lançamento deve ser associado a uma conta bancária ou a um cartão de crédito."
            )

        return cleaned_data


class CSVImportForm(forms.Form):
    # Campo para o usuário selecionar a conta de destino
    conta_bancaria = forms.ModelChoiceField(
        queryset=ContaBancaria.objects.none(),  # Será filtrado na view
        label="Importar para a Conta",
        empty_label="--- Selecione a Conta ---",
        widget=forms.Select(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm'})
    )
    # Campo para o upload do arquivo
    csv_file = forms.FileField(
        label="Selecione o arquivo CSV",
        widget=forms.FileInput(attrs={'class': 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'})
    )

    def __init__(self, *args, user=None, **kwargs):
        """Filtra o queryset de contas para mostrar apenas as do usuário logado."""
        super().__init__(*args, **kwargs)
        if user:
            self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(usuario=user)

class ConciliacaoForm(forms.Form):
    # Usamos CharField para data para usar o widget de texto com tipo 'date'
    data_caixa = forms.CharField(label="Data Efetiva", widget=forms.TextInput(attrs={'type': 'date', 'class': 'input-tailwind'}))
    valor = forms.DecimalField(label="Valor Efetivo", widget=forms.NumberInput(attrs={'class': 'input-tailwind'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplica as classes do Tailwind a todos os campos
        tailwind_classes = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = tailwind_classes
