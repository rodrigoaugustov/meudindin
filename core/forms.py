# core/forms.py

import os
from datetime import date
from django import forms
from django.db.models import Q
from django.urls import reverse
from django.utils.html import format_html

from .models import Fatura, Lancamento, Categoria, ContaBancaria, CartaoCredito, RegraCategoria
from . import services

class TailwindFormMixin:
    """Mixin para aplicar classes CSS do Tailwind a todos os campos de um formulário."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tailwind_classes = "mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
        for field_name, field in self.fields.items():
            # Aplica a classe apenas se o widget não tiver uma classe definida
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = tailwind_classes


class RegraCategoriaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = RegraCategoria
        fields = ['texto_regra', 'categoria']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['categoria'].queryset = Categoria.objects.filter(
                Q(usuario=user) | Q(usuario__isnull=True)
            ).order_by('nome')


class RegraCategoriaModalForm(RegraCategoriaForm):
    """Formulário específico para o modal, com IDs diferentes para evitar conflitos."""
    aplicar_retroativo = forms.BooleanField(required=False, initial=True, label="Aplicar esta regra a lançamentos existentes?")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Adiciona IDs específicos para o modal
        self.fields['texto_regra'].widget.attrs['id'] = 'id_texto_regra_modal'
        self.fields['categoria'].widget.attrs['id'] = 'id_categoria_modal'


class ContaBancariaForm(TailwindFormMixin, forms.ModelForm):
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
        
        # Itera sobre todos os campos do formulário e adiciona as classes
        for field_name, field in self.fields.items():
            # Adiciona placeholders para uma melhor UX
            if field_name == 'agencia':
                field.widget.attrs['placeholder'] = '0001 (Opcional)'
            if field_name == 'numero_conta':
                field.widget.attrs['placeholder'] = '12345-6'
            if field_name == 'saldo_inicial':
                field.widget.attrs['placeholder'] = '0,00'
            if field_name == 'data_saldo_inicial':
                field.widget.attrs['type'] = 'date'

class CartaoCreditoForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = CartaoCredito
        fields = ['nome_cartao', 'limite', 'dia_fechamento', 'dia_vencimento', 'conta_pagamento']
        labels = {
            'nome_cartao': 'Nome do Cartão (Apelido)',
            'limite': 'Limite do Cartão (R$)',
            'dia_fechamento': 'Dia do Fechamento da Fatura',
            'dia_vencimento': 'Dia do Vencimento da Fatura',
            'conta_pagamento': 'Conta para Pagamento da Fatura',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['conta_pagamento'].queryset = ContaBancaria.objects.filter(usuario=user)
            self.fields['conta_pagamento'].empty_label = "--- Selecione uma conta ---"

class CategoriaForm(TailwindFormMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nome']
        labels = {'nome': 'Nome da Categoria'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome'].widget.attrs['placeholder'] = 'Ex: Alimentação, Moradia, Lazer...'


class CategoriaModelChoiceField(forms.ModelChoiceField):
    """Campo customizado para exibir apenas o nome da categoria no dropdown."""
    def label_from_instance(self, obj):
        return obj.nome

class LancamentoForm(TailwindFormMixin, forms.ModelForm):
    # Usando o campo customizado para as categorias
    categoria = CategoriaModelChoiceField(
        queryset=Categoria.objects.none(), # O queryset será definido no __init__
        required=True, # Categoria agora é obrigatória
        empty_label=None # Remove a opção "---------"
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

    # --- Novos campos para recorrência ---
    REPETICAO_CHOICES = [
        ('UNICA', 'Única'),
        ('RECORRENTE', 'Recorrente'),
    ]
    PERIODICIDADE_CHOICES = [
        ('MENSAL', 'Mensal'),
        ('DIARIA', 'Diária'),
        ('SEMANAL', 'Semanal'),
        ('SEMESTRAL', 'Semestral'),
        ('ANUAL', 'Anual'),
    ]

    repeticao = forms.ChoiceField(
        choices=REPETICAO_CHOICES, required=True,
        label="Repetição", initial='UNICA'
    )
    periodicidade = forms.ChoiceField(
        choices=PERIODICIDADE_CHOICES, required=False,
        label="Periodicidade", initial='MENSAL'
    )
    quantidade_repeticoes = forms.IntegerField(
        required=False, label="Quantidade de Repetições", min_value=2, initial=2,
        help_text="Número total de parcelas, incluindo a atual."
    )

    # Campo para seleção de fatura
    fatura = forms.ModelChoiceField(
        queryset=Fatura.objects.none(),
        required=False,
        label="Fatura de Destino",
        help_text="Selecione a fatura para este lançamento. A fatura padrão é sugerida pela data da compra."
    )    
    # Campo oculto para controlar o fluxo de reabertura de fatura
    reabrir_fatura_confirmado = forms.BooleanField(required=False, widget=forms.HiddenInput())


    class Meta:
        model = Lancamento
        fields = [
            'descricao', 'valor', 'tipo', 'data_competencia', 'data_caixa',
            'categoria', 'conta_bancaria', 'cartao_credito', 'fatura'
        ]
        widgets = {
            'data_competencia': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descricao': forms.TextInput(attrs={'placeholder': 'Ex: Compra no supermercado'}),
            'valor': forms.NumberInput(attrs={'placeholder': '150,75'}),
        }

    def __init__(self, *args, user=None, conta=None, cartao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user # Armazena o usuário para uso em outras partes do form, como o clean().
        
        # Lógica para customizar o formulário baseado no contexto
        if conta:
            self.fields['conta_bancaria'].widget = forms.HiddenInput()
            self.fields['conta_bancaria'].initial = conta.pk
            self.fields['data_competencia'].label = "Data"
            del self.fields['cartao_credito']
            del self.fields['data_caixa']
            del self.fields['fatura'] # Fatura não se aplica a conta corrente
        elif cartao:
            self.fields['cartao_credito'].widget = forms.HiddenInput()
            self.fields['cartao_credito'].initial = cartao.pk
            self.fields['data_competencia'].label = "Data da Compra"
            del self.fields['conta_bancaria']
            del self.fields['data_caixa']

            # Configura o queryset e o valor inicial para o campo 'fatura'
            initial_fatura = None
            if self.instance and self.instance.pk and self.instance.fatura:
                initial_fatura = self.instance.fatura
            else:
                # Para novos lançamentos, calcula a fatura padrão com base na data atual ou inicial
                temp_data_competencia = kwargs.get('initial', {}).get('data_competencia') or date.today()
                temp_lancamento = Lancamento(
                    usuario=self.user,
                    cartao_credito=cartao,
                    data_competencia=temp_data_competencia
                )
                initial_fatura = services.get_or_create_fatura_aberta(temp_lancamento)
            
            # Constrói o queryset para 'fatura': fatura padrão + 2 anteriores + 2 próximas
            faturas_qs = Fatura.objects.filter(cartao=cartao).order_by('-data_vencimento') # Base queryset
            all_faturas_ordered = list(faturas_qs)
            
            selected_faturas_pks = set()
            if initial_fatura:
                try:
                    # Encontra o índice da fatura inicial na lista ordenada
                    idx = all_faturas_ordered.index(initial_fatura)
                    # Pega uma "fatia" de faturas ao redor da inicial
                    faturas_slice = all_faturas_ordered[max(0, idx - 2):min(len(all_faturas_ordered), idx + 3)]
                    # Adiciona os PKs da fatia ao nosso conjunto
                    selected_faturas_pks.update(f.pk for f in faturas_slice)
                except ValueError:
                    # A fatura inicial pode ter sido recém-criada e não estar na lista, o que é ok.
                    pass
                selected_faturas_pks.add(initial_fatura.pk) # Garante que a fatura inicial esteja sempre presente
            
            self.fields['fatura'].queryset = Fatura.objects.filter(pk__in=selected_faturas_pks).order_by('-data_vencimento')
            self.fields['fatura'].initial = initial_fatura.pk if initial_fatura else None
            self.fields['fatura'].empty_label = "--- Selecione uma fatura ---"
        
        if user:
            # Filtra os querysets dos campos ForeignKey
            self.fields['categoria'].queryset = Categoria.objects.filter(
                Q(usuario=user) | Q(usuario__isnull=True)
            ).order_by('nome')
            if 'conta_bancaria' in self.fields:
                self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(usuario=user)
            if 'cartao_credito' in self.fields:
                self.fields['cartao_credito'].queryset = CartaoCredito.objects.filter(usuario=user)
            
    def clean(self):
        """
        Validação customizada para garantir que conta bancária e cartão de crédito
        sejam mutuamente exclusivos.
        """
        cleaned_data = super().clean()
        conta_bancaria = cleaned_data.get("conta_bancaria")
        cartao_credito = cleaned_data.get("cartao_credito")
        data_competencia = cleaned_data.get("data_competencia")

        # A validação de mútua exclusividade não é mais necessária da mesma forma,
        # pois o formulário agora remove um dos campos.
        # Mantemos a validação para o caso genérico.
        if conta_bancaria and cartao_credito and not (self.fields['conta_bancaria'].is_hidden or self.fields['cartao_credito'].is_hidden):
            # Se ambos os campos foram preenchidos, levanta um erro de validação
            raise forms.ValidationError(
                "Um lançamento não pode ser associado a uma conta e a um cartão de crédito ao mesmo tempo. Por favor, escolha apenas um."
            )
        
        if not conta_bancaria and not cartao_credito and not (self.fields['conta_bancaria'].is_hidden or self.fields['cartao_credito'].is_hidden):
            # Garante que pelo menos um dos dois seja preenchido
            raise forms.ValidationError(
                "Um lançamento deve ser associado a uma conta bancária ou a um cartão de crédito."
            )
        
        if conta_bancaria and data_competencia:
            cleaned_data['data_caixa'] = data_competencia

        # Validação e definição de data_caixa para lançamentos de cartão
        if cartao_credito and data_competencia and self.user:
            selected_fatura = cleaned_data.get('fatura')
            
            if selected_fatura:
                target_fatura = selected_fatura
            else:
                # Se nenhuma fatura foi explicitamente selecionada, determina a fatura padrão
                temp_lancamento = Lancamento(
                    usuario=self.user,
                    cartao_credito=cartao_credito,
                    data_competencia=data_competencia
                )
                target_fatura = services.get_or_create_fatura_aberta(temp_lancamento)
            
            # Define data_caixa com base na data de vencimento da fatura alvo
            cleaned_data['data_caixa'] = target_fatura.data_vencimento

            # Agora, valida o status da fatura alvo
            if target_fatura.status != 'ABERTA':
                # Fatura está fechada. Verifica se o usuário já confirmou a reabertura.
                if cleaned_data.get('reabrir_fatura_confirmado'):
                    # Usuário confirmou no modal. Tenta reabrir a fatura.
                    sucesso = services.reabrir_fatura(target_fatura)
                    if not sucesso:
                        # A reabertura falhou (ex: pagamento já conciliado). Gera um erro normal.
                        raise forms.ValidationError("Não foi possível reabrir a fatura, pois o pagamento já foi conciliado. Cancele a conciliação do pagamento para prosseguir.")
                    # Se a reabertura foi bem-sucedida, a validação passa e o lançamento será salvo.
                else:
                    # Primeira tentativa. Gera um erro especial para ser capturado pelo JavaScript.
                    raise forms.ValidationError(
                        'A fatura está fechada.', # Mensagem genérica, o JS usará os parâmetros.
                        code='fatura_fechada',
                        params={
                            'vencimento': target_fatura.data_vencimento.strftime('%d/%m/%Y'),
                            'pk': target_fatura.pk
                        }
                    )

        repeticao = cleaned_data.get('repeticao')
        if repeticao == 'RECORRENTE':
            periodicidade = cleaned_data.get('periodicidade')
            quantidade = cleaned_data.get('quantidade_repeticoes')
            if not periodicidade:
                self.add_error('periodicidade', 'Este campo é obrigatório para lançamentos recorrentes.')
            if not quantidade:
                self.add_error('quantidade_repeticoes', 'Este campo é obrigatório para lançamentos recorrentes.')

        return cleaned_data

class UnifiedImportForm(TailwindFormMixin, forms.Form):
    IMPORT_CHOICES = [
        ('csv', 'CSV (Planilha)'),
        ('ofx', 'OFX (Extrato Bancário)'),
    ]

    import_type = forms.ChoiceField(
        choices=IMPORT_CHOICES,
        label="Tipo de Importação"
    )
    conta_bancaria = forms.ModelChoiceField(
        queryset=ContaBancaria.objects.none(),
        label="Importar para a Conta",
        empty_label="--- Selecione a Conta ---"
    )
    import_file = forms.FileField(
        label="Selecione o Arquivo"
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['conta_bancaria'].queryset = ContaBancaria.objects.filter(usuario=user)
        # O mixin aplica uma classe padrão, mas podemos sobrescrevê-la para campos específicos.
        self.fields['import_file'].widget.attrs['class'] = 'mt-1 block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100'

    def clean(self):
        cleaned_data = super().clean()
        import_type = cleaned_data.get('import_type')
        import_file = cleaned_data.get('import_file')

        if import_type and import_file:
            # Obtém a extensão do arquivo
            file_name, file_extension = os.path.splitext(import_file.name)
            file_extension = file_extension.lower() # Converte para minúsculas para comparação sem distinção de maiúsculas/minúsculas

            expected_extension_map = {
                'csv': '.csv',
                'ofx': '.ofx',
            }
            expected_extension = expected_extension_map.get(import_type)

            if expected_extension and file_extension != expected_extension:
                import_type_display = dict(self.IMPORT_CHOICES).get(import_type, import_type.upper())
                self.add_error('import_file', f"O arquivo selecionado não corresponde ao tipo de importação '{import_type_display}'. Por favor, selecione um arquivo com a extensão '{expected_extension}'.")
        return cleaned_data

class ConciliacaoForm(TailwindFormMixin, forms.Form):
    # Usando DateField com o widget correto para melhor validação e consistência.
    data_caixa = forms.DateField(
        label="Data Efetiva",
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')
    )
    valor = forms.DecimalField(label="Valor Efetivo")